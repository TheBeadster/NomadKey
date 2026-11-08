package network.columba.app.ui.components

import android.app.Activity
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import network.columba.app.nfc.NomadKeyShareActivity
import network.columba.app.nfc.NomadKeySharedAddress

@Composable
fun NomadKeyTagFlow(destination:String?=null,onDismiss:()->Unit,onOpen:(String)->Unit={},onFido:()->Unit) {
    val context=LocalContext.current
    var launched by remember { mutableStateOf(false) }
    val launcher=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if(result.resultCode==Activity.RESULT_OK && result.data?.getStringExtra("kind")=="fido") onFido()
        else if(destination==null && result.resultCode==Activity.RESULT_OK && result.data?.getStringExtra("kind")=="public") {
            val address=runCatching { NomadKeySharedAddress.validate(result.data?.getStringExtra("destination").orEmpty()) }.getOrNull()
            if(address!=null) onOpen(address)
        }
        onDismiss()
    }
    fun start() {
        if(launched) return
        launched=true
        launcher.launch(Intent(context,NomadKeyShareActivity::class.java)
            .putExtra("action",if(destination==null) "read" else "write")
            .putExtra("destination",destination))
    }
    if(destination==null) LaunchedEffect(Unit) { start() }
    else if(!launched) AlertDialog(onDismissRequest=onDismiss,
        title={Text("Save site to NFC")},
        text={Column(Modifier.verticalScroll(rememberScrollState())) {
            Text("Site address:\n\n$destination\n\nA normal NFC tag gets a public address without a PIN. A FIDO security key uses protected storage and asks for its PIN.\n\nPresent your tag or key. Existing website data is not overwritten. Site login remains separate.")
        }},
        confirmButton={TextButton(onClick={start()}) { Text("Detect and save") }},
        dismissButton={TextButton(onClick=onDismiss) { Text("Cancel") }})
}
