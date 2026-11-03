from pathlib import Path
import stat

from .auth import Denied


class Content:
    """Explicit route manifest. No dynamic executable handlers or implicit directories."""
    def __init__(self, auth, root, routes):
        self.auth, self.root, self.routes = auth, Path(root).resolve(), routes
        for route, relative in routes.items():
            if not route.startswith(("/page/", "/file/", "/media/")) or any(x in route for x in ("..", "%", "?", "#", "\\")):
                raise ValueError("invalid route")
            self._path(relative)

    def _path(self, relative):
        path = self.root / relative
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != self.root.parent):
            raise Denied("symlink")
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise Denied("invalid content")
        if resolved.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise Denied("executable content disabled")
        return resolved

    def read(self, route, link, client, fields=None):
        self.auth.require(link, client)
        if fields not in (None, b"", {}):
            raise Denied("forms disabled")
        if route not in self.routes:
            raise Denied("unknown route")
        path = self._path(self.routes[route])
        with path.open("rb") as f:
            body = f.read(65537)
        if len(body) > 65536:
            raise Denied("content too large")
        self.auth.require(link, client)  # do not finish a read after expiry
        return body
