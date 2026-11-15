package com.mykolzyai.studio

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import coil.compose.AsyncImage

private val Bg = Color(0xFFFFFFFF)
private val SurfaceDark = Color(0xFFF4F4F4)
private val TextMain = Color(0xFF202123)
private val TextMuted = Color(0xFF737373)
private val Accent = Color(0xFF202123)

data class ChatMessage(val text: String, val fromUser: Boolean, val imageUri: android.net.Uri? = null)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { KolzaiChatScreen() }
    }
}

/**
 * Локальный справочный ответ без сетевого запроса и без имитации работы LLM.
 * Использует только встроенные уроки RobloxKnowledge.
 */
private fun offlineKnowledgeReply(query: String, hasImage: Boolean = false): String {
    if (hasImage) return "Фото прикреплено, но визуальная ИИ-модель пока не подключена. Я могу обработать текст и локальную базу Roblox, но не буду утверждать, что распознал изображение."

    LocalReasoningEngine.solveMathQuestion(query)?.let { result ->
        return buildString {
            appendLine("Решение")
            appendLine()
            appendLine("Разберём выражение по порядку действий:")
            result.steps.forEachIndexed { index, step ->
                appendLine("${index + 1}. $step")
            }
            appendLine()
            append("Ответ: ${result.answer}")
        }
    }

    val matches = RobloxKnowledge.search(query, limit = 3)
    if (matches.isEmpty()) {
        return "Пока не могу надёжно ответить на этот вопрос в автономном режиме. " +
            "Сейчас Kolzai умеет пошагово решать простые арифметические выражения " +
            "и искать сведения во встроенной базе Roblox. Полноценная языковая модель ещё не подключена."
    }

    return buildString {
        appendLine("Справка по Roblox · найдено: ${matches.size}")
        matches.forEachIndexed { index, lesson ->
            if (index > 0) appendLine()
            appendLine("${index + 1}. ${lesson.titleRu}")
            appendLine(lesson.explanationRu)
            appendLine("Пример Luau:")
            appendLine(lesson.exampleLuau)
            appendLine("Совет для Building: ${lesson.buildingTipRu}")
        }
        appendLine()
        append("Это проверяемая справка из локальной базы, а не свободное рассуждение языковой модели.")
    }
}

private fun wantsWebSearch(query: String): Boolean {
    val text = query.lowercase()
    return listOf("найди", "поищи", "поиск в интернете", "в интернете", "на сайтах",
        "источники", "ссылки", "последние новости", "актуальная информация",
        "что сейчас", "сегодня").any { it in text }
}

private fun webSearchReply(query: String): String {
    val results = WebSearchClient.search(query, limit = 5)
    if (results.isEmpty()) return "Поиск завершился, но поисковая система не вернула доступных результатов."
    return buildString {
        appendLine("Результаты поиска в интернете")
        appendLine("Нашёл ${results.size} страниц. Это выдержки из поисковой выдачи, а не проверенный фактологический вывод.")
        results.forEachIndexed { index, result ->
            appendLine()
            appendLine("${index + 1}. ${result.title}")
            if (result.snippet.isNotBlank()) appendLine(result.snippet)
            appendLine(result.url)
        }
        appendLine()
        append("Открой источники и сверяй важные сведения по нескольким независимым страницам.")
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KolzaiChatScreen() {
    var draft by remember { mutableStateOf("") }
    var chatPhotoUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var isThinking by remember { mutableStateOf(false) }
    var thinkingStage by remember { mutableStateOf("") }
    var showHistory by remember { mutableStateOf(false) }
    var messages by remember { mutableStateOf(listOf<ChatMessage>()) }
    val context = LocalContext.current
    val mainHandler = remember { Handler(Looper.getMainLooper()) }
    val chatPhotoPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri -> chatPhotoUri = uri }

    MaterialTheme(colorScheme = darkColorScheme(
        primary = Accent, background = Bg, surface = SurfaceDark,
        onBackground = TextMain, onSurface = TextMain
    )) {
        Scaffold(
            containerColor = Bg,
            topBar = {
                TopAppBar(
                    title = {
                        Column {
                            Text("Centerion", fontWeight = FontWeight.Bold, fontSize = 21.sp)
                            Text("ИИ-помощник", color = TextMuted, fontSize = 11.sp)
                        }
                    },
                    navigationIcon = {
                        Text("☰", color = TextMain, fontSize = 23.sp,
                            modifier = Modifier.clickable { showHistory = !showHistory }.padding(horizontal = 18.dp))
                    },
                    actions = {
                        Text("＋", color = TextMain, fontSize = 27.sp,
                            modifier = Modifier.clickable { messages = emptyList(); chatPhotoUri = null; draft = "" }
                                .padding(horizontal = 18.dp))
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Bg, titleContentColor = TextMain)
                )
            },
            bottomBar = {
                Column(Modifier.fillMaxWidth().background(Bg).padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 10.dp)) {
                        Row(
                            Modifier.fillMaxWidth().background(SurfaceDark, RoundedCornerShape(28.dp)).padding(horizontal = 15.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("＋", color = TextMuted, fontSize = 25.sp, modifier = Modifier.clickable { chatPhotoPicker.launch("image/*") }.padding(end = 10.dp))
                            Box(Modifier.weight(1f)) {
                                if (draft.isEmpty()) Text("Спроси Centerion", color = TextMuted)
                                BasicTextField(value = draft, onValueChange = { draft = it },
                                    modifier = Modifier.fillMaxWidth(),
                                    textStyle = LocalTextStyle.current.copy(color = TextMain, fontSize = 16.sp), maxLines = 5)
                            }
                            Spacer(Modifier.width(10.dp))
                            Box(Modifier.size(38.dp).background(if (draft.isBlank() && chatPhotoUri == null) Color(0xFFD9D9D9) else TextMain, CircleShape)
                                .clickable {
                                    if (!isThinking && (draft.isNotBlank() || chatPhotoUri != null)) {
                                        val question = draft.trim().ifBlank { "Расскажи, что можно сделать с прикреплённым фото." }
                                        val image = chatPhotoUri
                                        messages = messages + ChatMessage(question, true, image)
                                        draft = ""
                                        chatPhotoUri = null
                                        isThinking = true
                                        thinkingStage = if (image != null) "Отправляю фото в Centerion…" else "Centerion думает…"
                                        Thread {
                                            val answer = try {
                                                if (image != null) {
                                                    CenterionApi.sendPhoto(context, image, question)
                                                } else {
                                                    CenterionApi.sendMessage(question)
                                                }
                                            } catch (error: Exception) {
                                                "Не удалось связаться с Centerion: ${error.message ?: "проверь подключение к серверу"}. Попробуй ещё раз."
                                            }
                                            mainHandler.post {
                                                messages = messages + ChatMessage(answer, false)
                                                isThinking = false
                                                thinkingStage = ""
                                            }
                                        }.start()
                                    }
                                }, contentAlignment = Alignment.Center) {
                                Text("↑", color = Bg, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                        chatPhotoUri?.let { selected ->
                            AsyncImage(model = selected, contentDescription = "Фото к сообщению",
                                modifier = Modifier.size(58.dp).padding(top = 5.dp))
                        }
                        Text(if (isThinking) thinkingStage else "Centerion · помощник",
                            color = if (isThinking) Accent else TextMuted, fontSize = 10.sp,
                            modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 7.dp))
                }
            }
        ) { padding ->
            Row(Modifier.fillMaxSize().padding(padding)) {
                if (showHistory) {
                    Column(Modifier.width(210.dp).fillMaxHeight().background(Color(0xFFF7F7F7)).padding(14.dp)) {
                        Text("Новый чат", color = TextMain, modifier = Modifier.clickable {
                            messages = emptyList(); showHistory = false
                        }.padding(vertical = 14.dp))
                        Divider(color = Color.DarkGray)
                        Text("История появится здесь", color = TextMuted, fontSize = 13.sp, modifier = Modifier.padding(top = 16.dp))
                    }
                }
                Column(Modifier.weight(1f).fillMaxHeight()) {
                    if (messages.isEmpty()) {
                        Column(Modifier.fillMaxSize().padding(horizontal = 24.dp),
                            verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
                            Box(Modifier.size(58.dp).background(SurfaceDark, CircleShape), contentAlignment = Alignment.Center) {
                                Text("K", color = TextMain, fontWeight = FontWeight.Bold, fontSize = 29.sp)
                            }
                            Spacer(Modifier.height(18.dp))
                            Text("Чем могу помочь?", color = TextMain, fontSize = 25.sp, fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(9.dp))
                            Text("Centerion", color = TextMuted, fontSize = 14.sp)
                            Spacer(Modifier.height(26.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                SuggestionChip("Напиши текст") { draft = "Помоги написать текст" }
                                SuggestionChip("Придумай идею") { draft = "Придумай интересную идею" }
                            }
                            Spacer(Modifier.height(8.dp))
                            SuggestionChip("Помоги с кодом") { draft = "Помоги разобраться с кодом" }
                        }
                    } else {
                        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp),
                            contentPadding = PaddingValues(vertical = 18.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                            items(messages) { message ->
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start) {
                                    Column(Modifier.widthIn(max = 300.dp)
                                        .background(if (message.fromUser) SurfaceDark else Bg, RoundedCornerShape(18.dp)).padding(13.dp)) {
                                        message.imageUri?.let { image ->
                                            AsyncImage(model = image, contentDescription = "Прикреплённое фото",
                                                modifier = Modifier.fillMaxWidth().heightIn(max = 220.dp))
                                            Spacer(Modifier.height(8.dp))
                                        }
                                        Text(message.text, color = TextMain)
                                    }
                                }
                            }
                            item {
                                Text("Ответы могут быть ограничены текущими возможностями модели.", color = TextMuted,
                                    fontSize = 13.sp, modifier = Modifier.padding(vertical = 8.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChoicePill(label: String, selected: Boolean, onClick: () -> Unit) {
    Surface(color = if (selected) Color(0xFFE8E8E8) else SurfaceDark,
        shape = RoundedCornerShape(18.dp), modifier = Modifier.clickable(onClick = onClick)) {
        Text(label, color = TextMain, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp))
    }
}

@Composable
private fun SuggestionChip(label: String, onClick: () -> Unit) {
    Surface(color = SurfaceDark, shape = RoundedCornerShape(20.dp), modifier = Modifier.clickable(onClick = onClick)) {
        Text(label, color = TextMain, fontSize = 12.sp, modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp))
    }
}
