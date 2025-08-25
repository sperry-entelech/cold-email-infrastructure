# Python Setup Instructions for Cold Email System

## Quick Python Installation (Windows)

### Option 1: Official Python Installer (Recommended)
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 (latest stable)
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. Choose "Install for all users"
5. After install, restart Command Prompt

### Option 2: Microsoft Store
1. Open Microsoft Store
2. Search for "Python 3.11"
3. Install official Python 3.11
4. This automatically adds to PATH

## Verify Installation

Open Command Prompt and run:
```bash
python --version
pip --version
```

Should show Python 3.8+ and pip version.

## Install Cold Email System

1. **Navigate to project folder:**
```bash
cd "C:\Users\spder\Prospect-Intelligence-Engine"
```

2. **Run automated setup:**
```bash
python setup_cold_email_system.py
```

This will:
- Install all dependencies
- Create .env configuration file
- Set up directories
- Create sample data
- Test connections

## Manual Installation (if setup script fails)

1. **Install dependencies:**
```bash
pip install pandas requests python-dotenv openai
```

2. **Copy environment file:**
```bash
copy .env.example .env
```

3. **Edit .env file with your API keys**

## Next Steps After Python Setup

1. **Get your API keys:**
   - Azure OpenAI: From Azure portal
   - Instantly: From instantly.ai dashboard

2. **Configure .env file:**
   - Open .env in notepad
   - Replace placeholder values with real API keys

3. **Process your FindyLead data:**
```bash
python cold_email_processor.py
```

4. **Monitor performance:**
```bash
python email_performance_monitor.py
```

## Troubleshooting

### "Python not found"
- Restart Command Prompt after Python installation
- Ensure "Add to PATH" was checked during install

### "pip not found" 
```bash
python -m ensurepip --upgrade
```

### Import errors
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Permission errors
- Run Command Prompt as Administrator
- Or install Python "for current user only"

## System Requirements
- Windows 10/11
- Python 3.8+
- 1GB free space
- Internet connection for API calls

The automated setup script handles most configuration automatically!