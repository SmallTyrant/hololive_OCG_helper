package com.smalltyrant.hocgh.data

import com.smalltyrant.hocgh.model.DeckEntryRecord
import com.smalltyrant.hocgh.model.DeckLibraryRecord
import com.smalltyrant.hocgh.model.SavedDeckRecord
import org.json.JSONArray
import org.json.JSONObject

class DeckStorage(private val paths: AppPaths) {
    fun loadLibrary(): DeckLibraryRecord {
        val file = paths.deckLibraryFile
        if (!file.exists()) {
            return DeckLibraryRecord()
        }
        return runCatching {
            val text = file.readText()
            decodeLibrary(text)
        }.recoverCatching {
            val backup = java.io.File(file.parentFile, "${file.name}.bak")
            if (!backup.exists()) throw it
            decodeLibrary(backup.readText())
        }.getOrElse {
            DeckLibraryRecord()
        }
    }

    fun saveLibrary(library: DeckLibraryRecord): Boolean {
        val file = paths.deckLibraryFile
        val tmp = kotlin.runCatching { java.io.File(file.parentFile, "${file.name}.tmp") }.getOrNull()
            ?: return false
        val backup = kotlin.runCatching { java.io.File(file.parentFile, "${file.name}.bak") }.getOrNull()
        return runCatching {
            tmp.writeText(encodeLibrary(library))
            if (file.exists() && backup != null) {
                file.copyTo(backup, overwrite = true)
            }
            if (file.exists()) {
                file.delete()
            }
            tmp.renameTo(file)
        }.getOrElse {
            tmp.delete()
            false
        }
    }

    fun exportText(decks: List<SavedDeckRecord>): String {
        return encodeLibrary(DeckLibraryRecord(decks = decks))
    }

    fun importText(raw: String): List<SavedDeckRecord> {
        return decodeLibrary(raw).decks
    }

    private fun encodeLibrary(library: DeckLibraryRecord): String {
        val root = JSONObject()
        root.put("version", library.version)
        val decksArray = JSONArray()
        library.decks.forEach { deck ->
            val deckObj = JSONObject()
            deckObj.put("id", deck.id)
            deckObj.put("title", deck.title)
            deckObj.put("updatedAt", deck.updatedAt)
            val entries = JSONArray()
            deck.entries.forEach { entry ->
                val entryObj = JSONObject()
                entryObj.put("printId", entry.printId)
                entryObj.put("cardNumber", entry.cardNumber)
                entryObj.put("qty", entry.qty)
                entry.selectedRarity?.let { entryObj.put("selectedRarity", it) }
                entries.put(entryObj)
            }
            deckObj.put("entries", entries)
            decksArray.put(deckObj)
        }
        root.put("decks", decksArray)
        return root.toString(2)
    }

    private fun decodeLibrary(raw: String): DeckLibraryRecord {
        val root = JSONObject(raw)
        val version = root.optInt("version", 1)
        val decksArray = root.optJSONArray("decks") ?: JSONArray()
        val decks = mutableListOf<SavedDeckRecord>()
        for (i in 0 until decksArray.length()) {
            val deckObj = decksArray.optJSONObject(i) ?: continue
            val deckId = deckObj.optString("id", "").ifBlank { java.util.UUID.randomUUID().toString() }
            val title = deckObj.optString("title", "덱")
            val updatedAt = deckObj.optLong("updatedAt", System.currentTimeMillis())
            val entriesArray = deckObj.optJSONArray("entries") ?: JSONArray()
            val entries = mutableListOf<DeckEntryRecord>()
            for (j in 0 until entriesArray.length()) {
                val entryObj = entriesArray.optJSONObject(j) ?: continue
                val printId = entryObj.optLong("printId", 0L)
                val cardNumber = entryObj.optString("cardNumber", "")
                val qty = entryObj.optInt("qty", 0).coerceAtLeast(0)
                val selectedRarity = entryObj.optString("selectedRarity", "").ifBlank { null }
                if (qty > 0 && (printId > 0 || cardNumber.isNotBlank())) {
                    entries += DeckEntryRecord(
                        printId = printId,
                        cardNumber = cardNumber,
                        qty = qty,
                        selectedRarity = selectedRarity,
                    )
                }
            }
            decks += SavedDeckRecord(
                id = deckId,
                title = title,
                entries = entries,
                updatedAt = updatedAt,
            )
        }
        return DeckLibraryRecord(version = version, decks = decks)
    }
}
