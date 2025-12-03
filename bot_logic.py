import asyncio
import random
import json
import time
import threading
from datetime import datetime
from twitchio.ext import commands
import requests

class Bot(commands.Bot):
    def __init__(self, config, bot_config, status_callback):
        oauth_token = bot_config['oauth']
        if not oauth_token.startswith('oauth:'):
            oauth_token = f"oauth:{oauth_token}"
        
        super().__init__(token=oauth_token, prefix="!", initial_channels=[bot_config['channel']])
        self.bot_config = bot_config
        self.config = config
        self.status_callback = status_callback
        self.used_questions = set()
        self.messages_sent = 0
        self.questions_asked = 0
        self.is_active = True
        
        # Настройки из конфига
        self.twitch_emotes = ["LUL", "Kappa", "PogChamp", "KEKW", "BibleThump", "FeelsBadMan", "GG", "WutFace"]
        self.special_emotes = ["LUL", "KEKW"]
        self.global_cooldown = config['settings']['global_cooldown']
        self.emote_chance_special = config['settings']['emote_chance_special']
        self.emote_chance_normal = config['settings']['emote_chance_normal']
        self.max_emote_repeat = config['settings']['max_emote_repeat']
        
        # Глобальные переменные для предотвращения цепочек
        self.last_emote_time = 0
        self.message_buffer = []
        
    def log_activity(self, message):
        """Логирует активность бота"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {self.bot_config['nick']}: {message}\n"
        
        with open('bot_activity.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Обновляем статус
        self.status_callback(self.bot_config['nick'], 'activity', message)
    
    def update_status(self, key, value):
        """Обновляет статус бота"""
        self.status_callback(self.bot_config['nick'], key, value)
    
    def is_human_user(self, username):
        """Проверяет, является ли пользователь человеком"""
        bot_nicks = {bot['nick'].lower() for bot in self.config['bots'] if bot['enabled']}
        return username.lower() not in bot_nicks
    
    def is_emote_chain_possible(self):
        """Проверяет, не создадут ли боты цепочку эмодзи"""
        if len(self.message_buffer) < 2:
            return True
        
        last_two = self.message_buffer[-2:]
        last_is_emote = any(emote in last_two[-1].get('content', '') for emote in self.twitch_emotes)
        prev_is_emote = any(emote in last_two[-2].get('content', '') for emote in self.twitch_emotes)
        last_from_bot = not self.is_human_user(last_two[-1].get('author', ''))
        prev_from_bot = not self.is_human_user(last_two[-2].get('author', ''))
        
        if last_is_emote and prev_is_emote and last_from_bot and prev_from_bot:
            return False
        
        return True
    
    async def event_ready(self):
        """Вызывается при подключении бота"""
        self.log_activity(f"Подключен к каналу {self.bot_config['channel']}")
        self.update_status('status', 'connected')
        asyncio.create_task(self.send_questions_loop())
    
    async def send_questions_loop(self):
        """Цикл отправки вопросов"""
        # Начальная задержка
        await asyncio.sleep(random.randint(10, 30))
        
        while self.is_active:
            try:
                # Интервал из конфига бота
                interval_min = self.bot_config.get('questions_interval_min', 60)
                interval_max = self.bot_config.get('questions_interval_max', 120)
                question_delay = random.randint(interval_min, interval_max)
                
                await asyncio.sleep(question_delay)
                
                if not self.is_active:
                    break
                
                # Выбираем вопрос
                available = list(set(self.config['questions']) - self.used_questions)
                if not available:
                    self.used_questions.clear()
                    available = self.config['questions']
                
                question = random.choice(available)
                self.used_questions.add(question)
                
                # Отправляем вопрос
                channel = self.get_channel(self.bot_config['channel'])
                if channel:
                    await channel.send(question)
                    self.questions_asked += 1
                    self.update_status('questions', self.questions_asked)
                    self.log_activity(f"Отправил вопрос: {question}")
                    
            except Exception as e:
                self.log_activity(f"Ошибка в цикле вопросов: {str(e)}")
                await asyncio.sleep(60)
    
    async def try_send_emote_reply(self, message):
        """Пробует отправить эмодзи в ответ"""
        # Обновляем буфер
        self.message_buffer.append({
            'author': message.author.name,
            'content': message.content,
            'timestamp': time.time()
        })
        
        if len(self.message_buffer) > 10:
            self.message_buffer = self.message_buffer[-10:]
        
        # Проверяем от человека ли сообщение
        if not self.is_human_user(message.author.name):
            return
        
        # Ищем эмодзи в сообщении
        words = message.content.split()
        found_emotes = []
        
        for w in words:
            if w in self.twitch_emotes:
                found_emotes.append(w)
        
        if not found_emotes:
            return
        
        # Проверяем cooldown
        current_time = time.time()
        if current_time - self.last_emote_time < self.global_cooldown:
            return
        
        # Проверяем цепочку
        if not self.is_emote_chain_possible():
            return
        
        # Выбираем эмодзи и проверяем шанс
        chosen_emote = random.choice(found_emotes)
        chance = self.emote_chance_special if chosen_emote in self.special_emotes else self.emote_chance_normal
        
        if random.random() < chance:
            count = random.randint(1, self.max_emote_repeat)
            emote_message = " ".join([chosen_emote] * count)
            
            delay = random.randint(6, 15)
            await asyncio.sleep(delay)
            
            self.last_emote_time = time.time()
            
            channel = message.channel
            if channel:
                await channel.send(emote_message)
                self.messages_sent += 1
                self.update_status('messages', self.messages_sent)
                self.log_activity(f"Ответил эмодзи '{chosen_emote}' x{count}")
    
    async def event_message(self, message):
        """Обработка входящих сообщений"""
        if not message.author or message.author.name.lower() == self.bot_config['nick'].lower():
            return
        
        # Пробуем ответить эмодзи
        await self.try_send_emote_reply(message)
        
        # Проверяем обращение к боту
        content = message.content.strip()
        bot_mentioned = (
            self.bot_config['nick'].lower() in content.lower() or
            f"@{self.bot_config['nick'].lower()}" in content.lower()
        )
        
        if bot_mentioned and self.is_human_user(message.author.name):
            reply = await self.ai_answer(content, message.author.name)
            if message.channel:
                if len(reply) > 450:
                    reply = reply[:447] + "..."
                await message.channel.send(f"@{message.author.name} {reply}")
                self.log_activity(f"Ответил AI пользователю {message.author.name}")
        
        await self.handle_commands(message)
    
    async def ai_answer(self, user_text, username=None):
        """Генерация ответа через AI"""
        api_key = self.config['settings']['openrouter_api_key']
        model = self.config['settings']['model_name']
        
        system_msg = {
            "role": "system",
            "content": f"Ты дружелюбный чат-бот Twitch канала {self.bot_config['channel']}. Отвечай коротко, весело и понятно."
        }
        user_msg = {"role": "user", "content": f"{username}: {user_text}" if username else user_text}
        
        payload = {
            "model": model,
            "messages": [system_msg, user_msg],
            "temperature": 0.7,
            "max_tokens": 100
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                               headers=headers, 
                               data=json.dumps(payload), 
                               timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            return "Извини, не понял вопрос 😅"
        except Exception as e:
            self.log_activity(f"Ошибка AI: {str(e)}")
            return "Что-то пошло не так, попробуй позже 😢"
    
    async def stop(self):
        """Останавливает бота"""
        self.is_active = False
        self.update_status('status', 'stopped')
        self.log_activity("Остановлен")

class BotManager:
    def __init__(self, config):
        self.config = config
        self.bots = []
        self.is_running = False
        self.status_callbacks = {}
        
    def status_callback(self, bot_name, key, value):
        """Callback для обновления статуса"""
        # Сохраняем в файл
        try:
            with open('bot_status.json', 'r', encoding='utf-8') as f:
                status = json.load(f)
        except:
            status = {}
        
        if key == 'activity':
            status[f'{bot_name}_last_activity'] = value
            status[f'{bot_name}_last_update'] = datetime.now().isoformat()
        elif key in ['messages', 'questions']:
            status[f'{bot_name}_{key}'] = value
        elif key == 'status':
            status[bot_name] = value
        
        with open('bot_status.json', 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    
    async def run(self):
        """Запускает всех ботов"""
        self.is_running = True
        
        # Создаем ботов только для включенных аккаунтов
        enabled_bots = [b for b in self.config['bots'] if b['enabled']]
        
        if not enabled_bots:
            self.is_running = False
            return
        
        self.bots = []
        tasks = []
        
        for bot_config in enabled_bots:
            try:
                bot = Bot(self.config, bot_config, self.status_callback)
                self.bots.append(bot)
                tasks.append(bot.start())
                self.status_callback(bot_config['nick'], 'status', 'starting')
                print(f"Запускаю бота: {bot_config['nick']}")
            except Exception as e:
                print(f"Ошибка создания бота {bot_config['nick']}: {e}")
                self.status_callback(bot_config['nick'], 'status', 'error')
        
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                print(f"Ошибка в работе ботов: {e}")
        
        self.is_running = False
    
    def stop_all(self):
        """Останавливает всех ботов"""
        self.is_running = False
        
        async def stop_bots():
            stop_tasks = []
            for bot in self.bots:
                stop_tasks.append(bot.stop())
            
            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Запускаем остановку в отдельной задаче
        asyncio.run_coroutine_threadsafe(stop_bots(), asyncio.get_event_loop())