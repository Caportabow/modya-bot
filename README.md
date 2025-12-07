# 🤖 Modya - Your Efficient Chat Assistant

<div align="center">

![Modya](./materials/description%20picture/description%20picture.png)

**A versatile and efficient assistant for Telegram chats**

[![License](https://img.shields.io/badge/license-Custom-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 📖 About

Modya is a powerful Telegram bot built from the ground up because existing alternatives no longer met expectations. Designed with efficiency and versatility in mind, Modya brings advanced chat management capabilities to your Telegram groups.

## ✨ Features

- 🔧 **Comprehensive Command System** - Full suite of management and utility commands
- 📊 **Advanced Analytics** - Track and analyze chat activity patterns
- 🔔 **Smart Notifications** - Customizable maintenance and event alerts
- 👥 **User Management** - Automated moderation and activity monitoring
- 🐳 **Docker Ready** - Easy deployment with containerization
- 🔄 **Asynchronous Design** - Built with modern async/await patterns for optimal performance

For a complete list of commands and functions, visit the [official documentation](https://teletype.in/@caportabow/ModyaTheBot).

## 🚀 Installation

### Prerequisites

- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the repository**
   ```
   git clone https://github.com/Caportabow/modya-bot.git
   cd modya-bot
   ```

2. **Configure environment**
   ```
   cp docker-compose.yml.example docker-compose.yml
   ```
   
   Edit `docker-compose.yml` and `config.py` with your configuration:
   - Bot token from [@BotFather](https://t.me/botfather)
   - Other required settings

3. **Build and start**
   ```
   docker compose up -d --build
   ```

## 💡 Usage

### Running the Bot

Start the bot in detached mode:
```
docker compose up -d --build
```

View logs:
```
docker compose logs -f
```

Stop the bot:
```
docker compose down
```

### Sending Mailings

Execute mailings while the container is running:
```
docker exec -it modya python mailing.py
```

## 📚 Documentation

Detailed documentation, including all available commands and their usage, can be found at:
https://teletype.in/@caportabow/ModyaTheBot

## 🏗️ Tech Stack

- **Language**: Python 3.9+
- **Framework**: aiogram (async Telegram Bot API wrapper)
- **Database**: PostgreSQL with asyncpg
- **Deployment**: Docker & Docker Compose

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs by opening an issue
- Suggest new features
- Submit pull requests

## 📄 License

This project uses a custom license:
- ✅ Full code use in private projects
- ✅ Reuse of individual modules in non-commercial projects (with attribution)
- ❌ Use of artwork and images is prohibited

See [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Telegram**: [@ModyaTheBot](https://t.me/ModyaTheBot)
- **Documentation**: [teletype.in/@caportabow/ModyaTheBot](https://teletype.in/@caportabow/ModyaTheBot)
- **Issues**: [GitHub Issues](https://github.com/Caportabow/modya-bot/issues)

---

<div align="center">

Made with ❤️ by [Caportabow](https://github.com/Caportabow)

</div>
