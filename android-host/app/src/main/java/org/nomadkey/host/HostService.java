package org.nomadkey.host;

import android.app.*;
import android.content.*;
import android.os.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;

/** User-started service. No exported command or enrolment surface. */
public class HostService extends Service {
    public static volatile String state = "Stopped";
    public static volatile boolean running = false;
    private PowerManager.WakeLock wake;
    public static synchronized PyObject module(Context c) {
        if (!Python.isStarted()) Python.start(new AndroidPlatform(c.getApplicationContext()));
        return Python.getInstance().getModule("nomadkey.host");
    }
    public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("host", "Hosting status", NotificationManager.IMPORTANCE_LOW));
        PendingIntent open = PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);
        startForeground(1,new Notification.Builder(this,"host").setSmallIcon(android.R.drawable.ic_lock_lock)
            .setContentTitle("NomadKey Host DEV").setContentText("Secure hosting is active").setContentIntent(open).setOngoing(true).build());
        wake = getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "NomadKey:Host");
        wake.acquire(10 * 60 * 1000L);
    }
    public int onStartCommand(Intent i,int flags,int id) {
        if (running) return START_NOT_STICKY;
        running=true;state="Starting Reticulum...";
        String config=getSharedPreferences("host",0).getString("config","{}");
        new Thread(() -> {
            try {
                state=module(this).callAttr("start",getFilesDir().getAbsolutePath()+"/host",new PhoneBridge(this),config).toString();
                while(running) {
                    Thread.sleep(5000);
                    if (!wake.isHeld()) wake.acquire(10 * 60 * 1000L);
                    state=module(this).callAttr("status").toString();
                }
            } catch(Exception e) {state="Host could not start or stopped. Check configuration and permissions; stop and reopen to retry.";}
        },"host-runtime").start();
        return START_NOT_STICKY;
    }
    public IBinder onBind(Intent i) { return null; }
    public void onDestroy() {
        running=false;
        try {module(this).callAttr("shutdown");} catch(Exception ignored) {}
        if(wake!=null && wake.isHeld())wake.release();
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
        // RNS is process-global. Exit only this app so a restart is a clean instance
        // with no stale authentication; do not touch a shared instance in another app.
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
