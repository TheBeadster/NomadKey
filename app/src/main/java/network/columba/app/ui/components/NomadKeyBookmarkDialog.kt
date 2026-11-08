package network.columba.app.ui.components

import android.app.Activity
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.SecureFlagPolicy
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import network.columba.app.rns.api.NomadKeyBookmarkTransfer
import network.columba.app.rns.api.NomadKeyPins
import org.json.JSONObject

@Composable
fun NomadKeyBookmarkDialog(action:String, siteJson:String="", onDismiss:()->Unit, onComplete:(NomadKeyPins.Site)->Unit) {
    val context=LocalContext.current
    val owner=LocalLifecycleOwner.current
    var pin by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("My NomadNet site") }
    var verified by remember { mutableStateOf(false) }
    var waiting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    val site=remember(siteJson) { if(siteJson.isEmpty()) null else runCatching { NomadKeyPins.parse(JSONObject(siteJson)) }.getOrNull() }
    val launcher=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val value=NomadKeyBookmarkTransfer.takeResult();NomadKeyBookmarkTransfer.clear()
        if(result.resultCode==Activity.RESULT_OK && value!=null) {
            val imported=runCatching { NomadKeyPins.parse(JSONObject(value)) }.getOrNull()
            if(imported!=null) onComplete(imported)
        }
        onDismiss()
    }
    DisposableEffect(owner) {
        val observer=LifecycleEventObserver { _,event -> if(event==Lifecycle.Event.ON_STOP) pin="" }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer);pin="" }
    }
    if(!waiting) AlertDialog(
        properties=DialogProperties(securePolicy=SecureFlagPolicy.SecureOn),
        onDismissRequest={pin="";onDismiss()},
        title={Text(if(action=="read") "Read NFC saved address" else "Save verified site to NFC key")},
        text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            if(action=="save") {
                Text("Check this identity against a trusted source. The announce name alone is not proof.")
                Text(site?.destination ?: "No current site",fontFamily=FontFamily.Monospace)
                Text("Service public key")
                Text(site?.publicKey.orEmpty(),fontFamily=FontFamily.Monospace)
                OutlinedTextField(value=name,onValueChange={if(it.toByteArray().size<=64) name=it},label={Text("Saved site name")},singleLine=true)
                Row { Checkbox(checked=verified,onCheckedChange={verified=it});Text("I independently verified this full site identity") }
                Text("Creates a separate protected bookmark. Existing login keys and your NFC website are kept. Do not interrupt the save.")
            } else Text("Read trusted addresses saved on your own key. This does not log you in or create credentials.")
            OutlinedTextField(value=pin,onValueChange={pin=it},label={Text("Existing FIDO2 PIN")},singleLine=true,
                keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Password,autoCorrectEnabled=false),visualTransformation=PasswordVisualTransformation())
            if(error.isNotEmpty()) Text(error,color=MaterialTheme.colorScheme.error)
        }},
        confirmButton={TextButton(enabled=pin.isNotEmpty() && (action=="read" || (verified && site!=null && name.isNotBlank())),onClick={
            val record=if(action=="save") site!!.copy(name=name.trim()).json().toString() else ""
            NomadKeyBookmarkTransfer.prepare(action,pin,record);pin=""
            try {
                waiting=true
                launcher.launch(Intent().setClassName(context.packageName,"network.columba.app.rns.backend.py.NomadKeyBookmarkActivity"))
            } catch(_:Exception) { NomadKeyBookmarkTransfer.clear();waiting=false;error="This build does not support NFC saved addresses." }
        }) {Text(if(action=="read") "Read key" else "Save to key")}},
        dismissButton={TextButton(onClick={pin="";onDismiss()}) {Text("Cancel")}},
    )
}

@Composable
fun NomadKeySavedSitesDialog(onDismiss:()->Unit,onOpen:(String)->Unit) {
    val context=LocalContext.current
    val result=remember { runCatching { NomadKeyPins.all(context) } }
    AlertDialog(onDismissRequest=onDismiss,title={Text("Saved NFC sites")},text={
        Column(Modifier.verticalScroll(rememberScrollState())) {
            if(result.isFailure) Text("Saved trust data cannot be read. No site will be substituted.")
            else if(result.getOrThrow().isEmpty()) Text("Use Read NFC saved address to import a site from your key.")
            else result.getOrThrow().forEach { site ->
                TextButton(onClick={onDismiss();onOpen(site.destination)}) {
                    Column { Text(site.name);Text(site.destination,fontFamily=FontFamily.Monospace) }
                }
            }
        }
    },confirmButton={TextButton(onClick=onDismiss) {Text("Close")}})
}
