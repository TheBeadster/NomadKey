package org.nomadkey.host;

import android.app.*;
import android.nfc.*;
import android.nfc.tech.IsoDep;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

/** Private activity: only MainActivity can launch after device credential confirmation. */
public class KeyActivity extends Activity implements NfcAdapter.ReaderCallback {
    private NfcAdapter adapter;
    private EditText pin;
    private TextView status;
    private ProgressBar progress;
    private Button start;
    private String secret="",operation;
    private final AtomicBoolean busy=new AtomicBoolean(false);
    private volatile boolean armed=false;
    private volatile Bridge bridge;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable timeout=()->finishAttempt("Failed: timed out. Tap Try again to start another attempt.");
    public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        operation=getIntent().getStringExtra("operation");
        if(operation==null){finish();return;}
        adapter=NfcAdapter.getDefaultAdapter(this);
        LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(24,48,24,32);setContentView(box);
        status=new TextView(this);status.setTextSize(20);
        try{String action=new org.json.JSONObject(operation).getString("action");status.setText(switch(action){case "enroll"->"Enrol this security key";case "authorize_enroll"->"Approve a new security key";case "trust_sim"->"Trust the reviewed SIM";case "save_page"->"Save the protected page";case "remove"->"Revoke the selected credential";case "bookmark"->"Save this site's address on your key";default->"Local key operation";});}catch(Exception e){finish();return;}
        box.addView(status);
        pin=new EditText(this);pin.setHint("Security key PIN");pin.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);pin.setSaveEnabled(false);pin.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);box.addView(pin);
        progress=new ProgressBar(this);progress.setVisibility(View.GONE);box.addView(progress);
        start=new Button(this);start.setText("Present key");box.addView(start);start.setOnClickListener(v->arm());
        Button close=new Button(this);close.setText("Continue / close");box.addView(close);close.setOnClickListener(v->finish());
    }
    private void arm(){
        if(busy.get())return;
        if(adapter==null||!adapter.isEnabled()){status.setText("Enable NFC on this phone first.");return;}
        secret=pin.getText().toString();pin.getText().clear();
        if(secret.isEmpty()){status.setText("Enter the key PIN first.");return;}
        armed=true;start.setEnabled(false);status.setText("Present and hold your FIDO2 key. Up to 60 seconds.");
        Bundle options=new Bundle();options.putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY,250);
        adapter.enableReaderMode(this,this,NfcAdapter.FLAG_READER_NFC_A|NfcAdapter.FLAG_READER_NFC_B|NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK|NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS,options);
        handler.postDelayed(timeout,60000);
    }
    public void onTagDiscovered(Tag tag){
        if(!armed||!busy.compareAndSet(false,true))return;
        runOnUiThread(()->{status.setText("Working with key. Keep it steady...");progress.setVisibility(View.VISIBLE);});
        new Thread(()->{
            String result;
            try{
                IsoDep iso=IsoDep.get(tag);if(iso==null)throw new IOException();iso.connect();iso.setTimeout(5000);bridge=new Bridge(iso);
                result=HostService.module(this).callAttr("local",bridge,secret,operation).toString();
                result="Success\n"+result;
            }catch(Exception e){result="Failed. The operation may have reached the key: check the host before retrying. Re-enter the PIN and tap Try again.";}
            finally{if(bridge!=null)bridge.close();bridge=null;busy.set(false);}
            String finalResult=result;runOnUiThread(()->{
                if(!armed)return;
                secret="";progress.setVisibility(View.GONE);
                status.setText(finalResult+"\nRemove your key to continue.");
                // Keep NFC reader mode active until removal so an implant's NDEF
                // website is not dispatched to the default browser after CTAP.
                adapter.ignore(tag,750,()->finishAttempt(finalResult),handler);
            });
        },"host-nfc").start();
    }
    private void finishAttempt(String text){armed=false;secret="";handler.removeCallbacks(timeout);if(adapter!=null)adapter.disableReaderMode(this);if(bridge!=null)bridge.close();status.setText(text);progress.setVisibility(View.GONE);start.setEnabled(true);start.setText("Try again");}
    protected void onPause(){if(armed)finishAttempt("Cancelled when app left the foreground. Re-enter PIN to retry.");super.onPause();}
    protected void onDestroy(){handler.removeCallbacksAndMessages(null);secret="";pin.getText().clear();if(bridge!=null)bridge.close();super.onDestroy();}
    public static final class Bridge {
        private final IsoDep iso;
        Bridge(IsoDep i){iso=i;}
        public byte[] transceive(byte[] command)throws IOException{return iso.transceive(command);}
        public void close(){try{iso.close();}catch(Exception ignored){}}
    }
}
