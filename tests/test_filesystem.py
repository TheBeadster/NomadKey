import os
import pytest
from nomadkey.content import Content
from nomadkey.auth import Denied


class Permit:
    def require(self,*args): return 10


def test_manifest_cannot_escape_root(tmp_path):
    root=tmp_path/'pages'; root.mkdir(); (tmp_path/'secret').write_text('private')
    with pytest.raises(Denied): Content(Permit(),root,{'/page/index.mu':'../secret'})


@pytest.mark.skipif(os.name=='nt',reason='POSIX executable bits are enforced and tested on serving Pi')
def test_executable_handlers_never_run(tmp_path):
    script=tmp_path/'index.mu';script.write_text('#!/bin/sh\necho SHOULD_NOT_RUN');script.chmod(0o700)
    with pytest.raises(Denied): Content(Permit(),tmp_path,{'/page/index.mu':'index.mu'})


@pytest.mark.skipif(os.name=='nt',reason='Symlink creation requires privileges on this Windows test host')
def test_symlink_replacement_denied(tmp_path):
    root=tmp_path/'pages';root.mkdir();page=root/'index.mu';page.write_text('safe')
    content=Content(Permit(),root,{'/page/index.mu':'index.mu'})
    page.unlink();(tmp_path/'secret').write_text('private');page.symlink_to(tmp_path/'secret')
    with pytest.raises(Denied): content.read('/page/index.mu',b'',b'')
