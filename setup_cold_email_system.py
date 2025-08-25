#!/usr/bin/env python3
"""
Setup script for Cold Email System
Automates the initial configuration and testing
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from example"""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        overwrite = input("⚠️  .env file exists. Overwrite? (y/n): ").lower().strip()
        if overwrite != 'y':
            print("📝 Keeping existing .env file")
            return True
    
    if env_example.exists():
        try:
            env_example.read_text()
            with open(env_file, 'w') as f:
                f.write(env_example.read_text())
            print("✅ Created .env file from example")
            print("📝 IMPORTANT: Edit .env file with your actual API keys!")
            return True
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False
    else:
        print("❌ .env.example file not found")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = ["logs", "reports", "data"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ Created directory: {dir_name}")

def test_imports():
    """Test if all required modules can be imported"""
    print("\n🧪 Testing imports...")
    required_modules = [
        "pandas",
        "requests", 
        "openai",
        "dotenv"
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def validate_env_file():
    """Check if .env file has required variables"""
    print("\n🔍 Validating environment configuration...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_ENDPOINT", 
            "INSTANTLY_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            print("📝 Edit .env file with your actual API keys")
            return False
        
        print("✅ Environment variables configured")
        return True
        
    except ImportError:
        print("❌ python-dotenv not installed")
        return False

def test_api_connections():
    """Test API connections"""
    print("\n🌐 Testing API connections...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test Azure OpenAI
        print("Testing Azure OpenAI connection...")
        import openai
        openai.api_type = "azure"
        openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
        openai.api_version = "2023-12-01-preview"  
        openai.api_key = os.getenv('AZURE_OPENAI_KEY')
        
        # Simple test call (this might fail if model not deployed, but connection will work)
        try:
            response = openai.ChatCompletion.create(
                engine="gpt-4",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print("✅ Azure OpenAI connection successful")
        except Exception as e:
            if "model_not_found" in str(e).lower():
                print("⚠️  Azure OpenAI connected, but GPT-4 model not found. Deploy GPT-4 model in Azure.")
            else:
                print(f"❌ Azure OpenAI error: {e}")
        
        # Test Instantly
        print("Testing Instantly connection...")
        import requests
        instantly_key = os.getenv('INSTANTLY_API_KEY')
        if instantly_key:
            headers = {"Authorization": f"Bearer {instantly_key}"}
            response = requests.get("https://api.instantly.ai/api/v1/campaign/list", headers=headers)
            
            if response.status_code == 200:
                print("✅ Instantly connection successful")
            else:
                print(f"❌ Instantly connection failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing connections: {e}")
        return False

def create_sample_csv():
    """Create a sample CSV file for testing"""
    sample_data = """first_name,last_name,email,company_name,industry,website,title
John,Smith,john@testcompany.com,Test Company,Marketing,https://testcompany.com,CEO
Jane,Doe,jane@example.org,Example Agency,Consulting,https://example.org,Founder
Bob,Johnson,bob@services.net,Johnson Services,Professional Services,https://services.net,Owner"""
    
    with open("sample_leads.csv", "w") as f:
        f.write(sample_data)
    
    print("✅ Created sample_leads.csv for testing")

def display_next_steps():
    """Display next steps for user"""
    print("""
🎉 SETUP COMPLETE!

📋 NEXT STEPS:

1. 🔑 Configure API Keys:
   - Edit .env file with your actual credentials
   - Get Azure OpenAI key from Azure portal
   - Get Instantly API key from instantly.ai dashboard

2. 🚀 Test the System:
   - Run: python cold_email_processor.py
   - Use sample_leads.csv for initial testing
   - Monitor results with: python email_performance_monitor.py

3. 📊 Set up Campaigns in Instantly:
   - Create "enterprise-direct-pitch" campaign
   - Create "professional-nurture" campaign  
   - Create "educational-sequence" campaign
   - Update campaign IDs in .env file

4. 💬 Optional Slack Integration:
   - Create Slack webhook URL
   - Add SLACK_WEBHOOK_URL to .env for hot lead notifications

5. 📈 Scale Your System:
   - Start with 3 ZapMail mailboxes
   - Process your 2K FindyLead export
   - Monitor performance and optimize

🎯 EXPECTED RESULTS (Nick's Metrics):
- 1-2% reply rate target
- 1 meeting per 150 emails sent
- 10-20% close rate on meetings

📁 KEY FILES:
- cold_email_processor.py - Main lead processing script
- email_performance_monitor.py - Performance tracking
- sample_leads.csv - Test data
- .env - Your configuration (KEEP PRIVATE!)

Ready to start your cold email campaign following Nick's proven methodology! 🚀
    """)

def main():
    """Main setup function"""
    print("🚀 Cold Email System Setup")
    print("Following Nick's Proven Methodology")
    print("=" * 50)
    
    setup_steps = [
        ("Checking Python version", check_python_version),
        ("Installing dependencies", install_dependencies),  
        ("Creating .env file", create_env_file),
        ("Creating directories", create_directories),
        ("Testing imports", test_imports),
        ("Creating sample CSV", create_sample_csv),
    ]
    
    # Run setup steps
    for step_name, step_func in setup_steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"❌ Setup failed at: {step_name}")
            return False
    
    # Optional validation steps (don't fail setup)
    print(f"\n🔍 Running validation checks...")
    validate_env_file()
    test_api_connections()
    
    display_next_steps()
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)