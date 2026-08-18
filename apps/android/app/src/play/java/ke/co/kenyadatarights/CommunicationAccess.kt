package ke.co.kenyadatarights

import android.content.Context

object CommunicationAccess {
    val requiredPermissions: Array<String> = emptyArray()
    const val available = false

    fun scan(context: Context): SharedObservation = SharedObservation(emptySet(), emptySet())
}
