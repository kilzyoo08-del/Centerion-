package com.mykolzyai.studio

import android.content.Context
import android.net.Uri
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.UUID

/**
 * Клиент Android-приложения для Centerion API.
 * Адрес ngrok временный: после перезапуска туннеля его может потребоваться заменить.
 */
object CenterionApi {
    private const val BASE_URL = "https://driller-puzzling-exclaim.ngrok-free.dev"
    private const val CONNECT_TIMEOUT_MS = 30_000
    private const val READ_TIMEOUT_MS = 180_000

    fun checkHealth(): Boolean {
        val connection = (URL("$BASE_URL/health").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = CONNECT_TIMEOUT_MS
            connection.setRequestProperty("ngrok-skip-browser-warning", "true")
            connection.responseCode == HttpURLConnection.HTTP_OK
        } finally {
            connection.disconnect()
        }
    }

    fun sendMessage(message: String): String {
        val body = "message=${encode(message)}&user_id=${encode("android_user")}"
        val connection = (URL("$BASE_URL/answer").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty("ngrok-skip-browser-warning", "true")
            connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }


    fun sendPhoto(context: Context, uri: Uri, question: String): String =
        uploadMultipart(context, uri, question, "/media")

    fun sendFile(context: Context, uri: Uri, question: String): String {
        return uploadMultipart(context, uri, question, "/files")
    }

    fun generateCode(task: String, language: String = "python"): String {
        val body = "task=${encode(task)}&language=${encode(language)}"
        val connection = (URL("$BASE_URL/code").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty("ngrok-skip-browser-warning", "true")
            connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }

    fun rememberFact(fact: String): String {
        val body = "user_id=${encode("android_user")}&fact=${encode(fact)}"
        val connection = (URL("$BASE_URL/memory").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty("ngrok-skip-browser-warning", "true")
            connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }

    private fun uploadMultipart(context: Context, uri: Uri, question: String, endpoint: String): String {
        val boundary = "Centerion-${UUID.randomUUID()}"
        val connection = (URL("$BASE_URL$endpoint").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty("ngrok-skip-browser-warning", "true")
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            connection.outputStream.use { output ->
                fun writeText(name: String, value: String) {
                    output.write("--$boundary\r\n".toByteArray())
                    output.write("Content-Disposition: form-data; name=\"$name\"\r\n\r\n".toByteArray())
                    output.write(value.toByteArray(Charsets.UTF_8))
                    output.write("\r\n".toByteArray())
                }
                writeText("question", question)
                writeText("user_id", "android_user")
                val mime = context.contentResolver.getType(uri) ?: "application/octet-stream"
                val fileName = "centerion_upload"
                output.write("--$boundary\r\n".toByteArray())
                output.write("Content-Disposition: form-data; name=\"file\"; filename=\"$fileName\"\r\n".toByteArray())
                output.write("Content-Type: $mime\r\n\r\n".toByteArray())
                val input = context.contentResolver.openInputStream(uri)
                    ?: throw IllegalStateException("Не удалось открыть выбранный файл")
                input.use { it.copyTo(output) }
                output.write("\r\n--$boundary--\r\n".toByteArray())
            }
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }

    private fun readResponse(connection: HttpURLConnection): String {
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val raw = stream?.use { input ->
            BufferedReader(InputStreamReader(input, Charsets.UTF_8)).readText()
        }.orEmpty()

        if (status !in 200..299) {
            return "Centerion API вернул ошибку HTTP $status: $raw"
        }

        return try {
            val json = JSONObject(raw)
            when {
                json.has("answer") -> json.optString("answer")
                json.has("response") -> json.optString("response")
                json.has("result") -> json.optString("result")
                else -> raw
            }
        } catch (_: Exception) {
            raw.ifBlank { "Centerion вернул пустой ответ." }
        }
    }

    private fun encode(value: String): String =
        URLEncoder.encode(value, "UTF-8")
}
