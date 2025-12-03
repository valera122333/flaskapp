import os
import json
import asyncio
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-123')

# Глобальные переменные для управления ботами
bot_tasks = []
bot_instances = []
bot_status = {}
bot_control_lock = threading.Lock()

# Файлы конфигурации
CONFIG_FILE = 'config.json'
STATUS_FILE = 'bot_status.json'

def load_config():
    """Загружает конфигурацию из файла"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Создаем дефолтную конфигурацию
        default_config = {
            "bots": [
                {
                    "nick": "zona_petuhov228",
                    "channel": "eklerchickid",
                    "oauth": "oauth:jpbvj0xogu6v2q9ckv9dv4lwl85bjs",
                    "enabled": True,
                    "questions_interval_min": 60,
                    "questions_interval_max": 120
                } 
            ],
            "settings": {
                "global_cooldown": 10,
                "emote_chance_special": 0.8,
                "emote_chance_normal": 0.3,
                "max_emote_repeat": 3,
                "openrouter_api_key": "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",
                "model_name": "meta-llama/llama-3.1-8b-instruct"
            },
            "questions": [
                "а на ком ваще ты любишь плеить?",
    "на ком можно птсов нарастить в 2к25?",
    "ждешь чтоб тинкеру ракетки вернули?",
    "на ком у тебя винрейт топовый ?",
    "чо новый патч ждешь?",
    "пздц патча нету, зато габен на новой яхте)",
    "почему все говорят что дота умирает, если в нее вон все играют и птсы стараются апнуть",
    "а скока у тебя птсов щас вообще?",
    "как прошел твой день брат",
    "расскажи интересную историю из жизни",
    "ты че всю жизнь только в доту играешь?",
    "шо может протащить тебя бомжа?)",
    "На твоем рейте ставят варды вообще?)",
    "когда гайд уже будет то емае",
    "какой у тебя максимальный рейтинг?",
    "кто твой любимый про-игрок, миракл да?))",
    "пока габен катается на яхте, мы застряли в одном патче да...",
    "а че там с про сценой вообще...",
    "а вот были времена когда денди на пудже всех выносил..эх сук",
    "тупо игра скатилась , нет обнов, уже бля на кери лионах играют пацаны и мид на вайпере ходят)",
    "а кто вообще твои сигны , на ком ты птсы апал",
    "ты в пати с подписчиками играешь вообще?",
    "когда-нибудь клаву разбивал из-за этой жестокой игры?(",
    "удачного стрима брат, апай птсы",
    "че думаешь про justhateme?",
    "какая обнова реально была топовая? ну типа игра после нее ожила, какой вообще тебе патч запомнился?",
    "а квшки играешь вообще? пробовал себя в турике каком-нибудь может?",
    "насколько сильно 1к отличается от твоих 6к?",
    "назови топ 5 кери для апа ммр",
    "назови топ 5 мидеров для апа ммр",
    "чо пати можно залететь некст?",
    "че там когда уже титана то апнем?",
    "научишь на шторме нас играть?",
    "а почему у тебя в тиктоке нет гайдов на пуджа(",
    "а шо по морали? после доты еще жить хочется?",
    "когда уже арка нормального апнут, задолбало...",
    "сколько у тебя блокировок акков ваще было? не скрывайся)",
    "ты вот сам руинишь иногда или всегда святой?",
    "а ты плеил когда-нибудь на героях, которых вообще не понимаешь?",
    "ты вообще на саппортах играешь? или чисто 1-2 позиция?",
    "сколько у тебя фидеров за сегодня было? 2-3?)",
    "под какие песни нравится тушить пацанов",
    "какой самый странный пик ты видел у себя в команде",
    "когда уже марси удалят? ты за или против?)",
    "ты часто репортишь? или только когда прям кипит?",
    "как не посмотрю у тебя всегда бомж скины, тебе не нрав косметика??",
    "какой герой тебе кажется самым переоцененным?",
    "кого бы ты удалил из доты, если бы дали выбор?",
    "как часто у тебя были камбеки с -20к? веришь вообще в чудеса?",
    "какой герой у тебя вызывает флэшбеки и боль?)",
    "когда уже начнёшь соло тащить, а не на тиммейтов надеяться?))",
    "какой у тебя худший герой? тот, на котором позор ваще)",
    "ты в каком году вообще начал играть в доту? с 2015 или позже?",
    "как думаешь, дота умрёт или габен воскресит?",
    "ты считаешь что лоу приорити заслуженное место для наказаний?))",
    "LUL",
    "когда последний раз пикал инвокера? руки помнят?)",
    "как тебе текущий мета-пул? есть раздражающие герои?",
    "а есть герой, которого ты вообще боишься видеть на керри?",
    "когда уже будешь катать свой турнир, давай комьюнити соберём?",
            ]
        }
        save_config(default_config)
        return default_config

def save_config(config):
    """Сохраняет конфигурацию в файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def save_status():
    """Сохраняет статус ботов в файл"""
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bot_status, f, indent=2, ensure_ascii=False)

def load_status():
    """Загружает статус ботов из файла"""
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Загружаем начальный статус
bot_status.update(load_status())

# Импортируем логику ботов
try:
    from bot_logic import BotManager
    bot_manager = None
except ImportError as e:
    logger.error(f"Не удалось импортировать логику ботов: {e}")
    bot_manager = None

@app.route('/')
def index():
    """Главная страница с панелью управления"""
    config = load_config()
    return render_template('index.html', 
                         config=config, 
                         bot_status=bot_status,
                         is_running=bot_manager is not None and bot_manager.is_running)

@app.route('/api/status')
def get_status():
    """API для получения статуса"""
    status_info = {
        "is_running": bot_manager is not None and bot_manager.is_running,
        "bots": {},
        "timestamp": datetime.now().isoformat()
    }
    
    config = load_config()
    for bot in config['bots']:
        bot_name = bot['nick']
        status_info['bots'][bot_name] = {
            'enabled': bot['enabled'],
            'status': bot_status.get(bot_name, 'stopped'),
            'last_activity': bot_status.get(f'{bot_name}_last_activity', 'Нет данных'),
            'messages_sent': bot_status.get(f'{bot_name}_messages', 0),
            'questions_asked': bot_status.get(f'{bot_name}_questions', 0)
        }
    
    return jsonify(status_info)

@app.route('/api/start', methods=['POST'])
def start_bots():
    """API для запуска ботов"""
    global bot_manager
    
    if bot_manager and bot_manager.is_running:
        return jsonify({"success": False, "message": "Боты уже запущены"})
    
    try:
        config = load_config()
        
        # Инициализируем менеджер ботов
        from bot_logic import BotManager
        bot_manager = BotManager(config)
        
        # Запускаем ботов в отдельном потоке
        bot_thread = threading.Thread(target=run_bots, args=(bot_manager,), daemon=True)
        bot_thread.start()
        
        # Обновляем статус
        for bot in config['bots']:
            if bot['enabled']:
                bot_status[bot['nick']] = 'starting'
        
        save_status()
        
        return jsonify({
            "success": True, 
            "message": f"Запуск {len([b for b in config['bots'] if b['enabled']])} ботов..."
        })
        
    except Exception as e:
        logger.error(f"Ошибка запуска ботов: {e}")
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})

@app.route('/api/stop', methods=['POST'])
def stop_bots():
    """API для остановки ботов"""
    global bot_manager
    
    if not bot_manager or not bot_manager.is_running:
        return jsonify({"success": False, "message": "Боты не запущены"})
    
    try:
        bot_manager.stop_all()
        
        # Обновляем статус
        config = load_config()
        for bot in config['bots']:
            if bot['enabled']:
                bot_status[bot['nick']] = 'stopping'
        
        save_status()
        
        return jsonify({"success": True, "message": "Остановка ботов..."})
        
    except Exception as e:
        logger.error(f"Ошибка остановки ботов: {e}")
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """API для управления конфигурацией"""
    if request.method == 'GET':
        config = load_config()
        return jsonify(config)
    
    elif request.method == 'POST':
        try:
            new_config = request.get_json()
            
            # Валидация конфигурации
            if 'bots' not in new_config or 'settings' not in new_config:
                return jsonify({"success": False, "message": "Неверный формат конфигурации"})
            
            save_config(new_config)
            
            # Если боты запущены, перезапускаем с новой конфигурацией
            if bot_manager and bot_manager.is_running:
                bot_manager.stop_all()
                time.sleep(2)
                bot_manager.config = new_config
                bot_thread = threading.Thread(target=run_bots, args=(bot_manager,), daemon=True)
                bot_thread.start()
            
            return jsonify({"success": True, "message": "Конфигурация обновлена"})
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})

@app.route('/api/bot/<bot_name>/toggle', methods=['POST'])
def toggle_bot(bot_name):
    """API для включения/выключения конкретного бота"""
    try:
        config = load_config()
        
        for bot in config['bots']:
            if bot['nick'] == bot_name:
                bot['enabled'] = not bot['enabled']
                status = "включен" if bot['enabled'] else "выключен"
                
                save_config(config)
                
                # Если боты запущены, обновляем статус
                if bot_manager and bot_manager.is_running:
                    bot_status[bot_name] = 'enabled' if bot['enabled'] else 'disabled'
                    save_status()
                
                return jsonify({
                    "success": True, 
                    "message": f"Бот {bot_name} {status}",
                    "enabled": bot['enabled']
                })
        
        return jsonify({"success": False, "message": f"Бот {bot_name} не найден"})
        
    except Exception as e:
        logger.error(f"Ошибка переключения бота: {e}")
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})

@app.route('/api/logs')
def get_logs():
    """API для получения логов"""
    try:
        log_file = 'bot_activity.log'
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-100:]  # Последние 100 строк
            return jsonify({"success": True, "logs": logs})
        else:
            return jsonify({"success": True, "logs": ["Логи пока отсутствуют"]})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка чтения логов: {str(e)}"})

def run_bots(manager):
    """Запускает ботов в асинхронном цикле"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.run())
    except Exception as e:
        logger.error(f"Ошибка в потоке ботов: {e}")

if __name__ == '__main__':
    # Создаем необходимые файлы и папки
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Загружаем начальную конфигурацию
    load_config()
    
    # Запускаем Flask
    app.run(debug=True, host='0.0.0.0', port=5000)