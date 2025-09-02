#!/usr/bin/env python3
"""
Mailbox Configuration Helper for Cold Email System
Helps set up mailboxes, domains, and email authentication
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MailboxConfig:
    """Configuration for a single mailbox"""
    email: str
    provider: str  # zapmail, gmass, etc.
    status: str = "pending"  # pending, warming, active, issues
    daily_limit: int = 30
    warmup_days: int = 21
    domain: str = ""
    created_date: str = ""
    notes: str = ""

@dataclass
class DomainConfig:
    """Configuration for a sending domain"""
    domain: str
    registrar: str
    dns_configured: bool = False
    spf_record: str = ""
    dkim_record: str = ""
    dmarc_record: str = ""
    mx_record: str = ""
    status: str = "pending"  # pending, configured, verified
    notes: str = ""

class MailboxSetupHelper:
    """Helper class for mailbox and domain configuration"""
    
    def __init__(self):
        self.config_file = "mailbox_config.json"
        self.load_existing_config()
    
    def load_existing_config(self):
        """Load existing configuration or create empty config"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.mailboxes = [MailboxConfig(**mb) for mb in data.get('mailboxes', [])]
                self.domains = [DomainConfig(**dom) for dom in data.get('domains', [])]
        else:
            self.mailboxes = []
            self.domains = []
        
        logger.info(f"Loaded {len(self.mailboxes)} mailboxes and {len(self.domains)} domains")
    
    def save_config(self):
        """Save current configuration to file"""
        config_data = {
            'mailboxes': [asdict(mb) for mb in self.mailboxes],
            'domains': [asdict(dom) for dom in self.domains],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Configuration saved to {self.config_file}")
    
    def add_domain(self, domain: str, registrar: str = "") -> DomainConfig:
        """Add a new domain configuration"""
        # Check if domain already exists
        for existing in self.domains:
            if existing.domain.lower() == domain.lower():
                logger.warning(f"Domain {domain} already exists")
                return existing
        
        domain_config = DomainConfig(
            domain=domain.lower(),
            registrar=registrar,
            status="pending"
        )
        
        self.domains.append(domain_config)
        logger.info(f"Added domain: {domain}")
        return domain_config
    
    def add_mailbox(self, email: str, provider: str, domain: str = "", daily_limit: int = 30) -> MailboxConfig:
        """Add a new mailbox configuration"""
        # Extract domain from email if not provided
        if not domain:
            domain = email.split('@')[1] if '@' in email else ""
        
        # Check if mailbox already exists
        for existing in self.mailboxes:
            if existing.email.lower() == email.lower():
                logger.warning(f"Mailbox {email} already exists")
                return existing
        
        mailbox_config = MailboxConfig(
            email=email.lower(),
            provider=provider.lower(),
            domain=domain.lower(),
            daily_limit=daily_limit,
            created_date=datetime.now().isoformat(),
            status="pending"
        )
        
        self.mailboxes.append(mailbox_config)
        logger.info(f"Added mailbox: {email}")
        return mailbox_config
    
    def generate_dns_records(self, domain: str) -> Dict[str, str]:
        """Generate recommended DNS records for email authentication"""
        records = {}
        
        # SPF Record - Allow common email providers
        records['SPF'] = f"v=spf1 include:_spf.zapmail.co include:mailgun.org include:sendgrid.net ~all"
        
        # DMARC Record - Start with monitoring
        records['DMARC'] = f"v=DMARC1; p=none; rua=mailto:dmarc@{domain}; ruf=mailto:dmarc@{domain}; fo=1"
        
        # MX Record suggestions
        records['MX'] = "10 mx.zapmail.co"  # Default for ZapMail
        
        # DKIM - Will be provided by email provider
        records['DKIM_NOTE'] = "DKIM record will be provided by your email provider (ZapMail, etc.)"
        
        return records
    
    def update_domain_dns(self, domain: str, dns_records: Dict[str, str]):
        """Update domain with DNS record information"""
        for domain_config in self.domains:
            if domain_config.domain == domain.lower():
                domain_config.spf_record = dns_records.get('SPF', '')
                domain_config.dmarc_record = dns_records.get('DMARC', '')
                domain_config.mx_record = dns_records.get('MX', '')
                domain_config.dkim_record = dns_records.get('DKIM', '')
                domain_config.dns_configured = True
                domain_config.status = "configured"
                logger.info(f"Updated DNS records for {domain}")
                return domain_config
        
        logger.error(f"Domain {domain} not found")
        return None
    
    def get_setup_checklist(self) -> Dict:
        """Generate setup checklist based on current configuration"""
        checklist = {
            'domains': [],
            'mailboxes': [],
            'next_steps': []
        }
        
        # Domain checklist
        for domain in self.domains:
            domain_status = {
                'domain': domain.domain,
                'status': domain.status,
                'tasks': []
            }
            
            if not domain.dns_configured:
                domain_status['tasks'].append("Configure DNS records (SPF, DMARC, MX)")
            if domain.status == 'pending':
                domain_status['tasks'].append("Verify domain ownership")
            
            checklist['domains'].append(domain_status)
        
        # Mailbox checklist  
        for mailbox in self.mailboxes:
            mailbox_status = {
                'email': mailbox.email,
                'status': mailbox.status,
                'provider': mailbox.provider,
                'tasks': []
            }
            
            if mailbox.status == 'pending':
                mailbox_status['tasks'].append("Create mailbox with provider")
                mailbox_status['tasks'].append("Configure SMTP settings")
            if mailbox.status == 'warming':
                mailbox_status['tasks'].append(f"Continue warmup ({mailbox.warmup_days} days)")
            
            checklist['mailboxes'].append(mailbox_status)
        
        # Overall next steps
        if len(self.domains) == 0:
            checklist['next_steps'].append("Purchase domains for cold email")
        if len(self.mailboxes) == 0:
            checklist['next_steps'].append("Set up mailboxes with ZapMail or similar")
        if any(d.status == 'pending' for d in self.domains):
            checklist['next_steps'].append("Configure DNS records for domains")
        if any(mb.status in ['pending', 'warming'] for mb in self.mailboxes):
            checklist['next_steps'].append("Complete mailbox setup and warmup")
        
        return checklist
    
    def print_setup_guide(self):
        """Print comprehensive setup guide"""
        print("🚀 Cold Email Mailbox Setup Guide")
        print("=" * 50)
        
        print("\n📋 CURRENT STATUS:")
        print(f"- Domains: {len(self.domains)}")
        print(f"- Mailboxes: {len(self.mailboxes)}")
        
        # Domain status
        if self.domains:
            print("\n🌐 DOMAINS:")
            for domain in self.domains:
                status_icon = "✅" if domain.status == "verified" else "⚠️" if domain.status == "configured" else "❌"
                print(f"  {status_icon} {domain.domain} ({domain.status})")
        
        # Mailbox status
        if self.mailboxes:
            print("\n📧 MAILBOXES:")
            for mailbox in self.mailboxes:
                status_icon = "✅" if mailbox.status == "active" else "🔄" if mailbox.status == "warming" else "❌"
                print(f"  {status_icon} {mailbox.email} - {mailbox.provider} ({mailbox.status})")
        
        # Setup checklist
        checklist = self.get_setup_checklist()
        
        if checklist['next_steps']:
            print("\n🎯 NEXT STEPS:")
            for i, step in enumerate(checklist['next_steps'], 1):
                print(f"  {i}. {step}")
        
        print("\n💰 RECOMMENDED SETUP (Nick's Method):")
        print("1. 🌐 Purchase 3-5 domains:")
        print("   - yourname-consulting.com")
        print("   - yourname-automation.com") 
        print("   - yourname-solutions.com")
        print("   - Cost: ~$15/month total")
        
        print("\n2. 📧 ZapMail Mailboxes:")
        print("   - Start with 3 mailboxes (30 emails/day each)")
        print("   - Consider pre-warmed mailboxes ($50-100 extra)")
        print("   - Cost: ~$90/month for 3 mailboxes")
        
        print("\n3. 🔧 DNS Configuration:")
        print("   - SPF: Allow ZapMail to send")
        print("   - DKIM: Provided by ZapMail")
        print("   - DMARC: Start with monitoring mode")
        print("   - MX: Point to ZapMail servers")
        
        print("\n4. 🎯 Instantly Setup:")
        print("   - Create campaigns for different lead types")
        print("   - Configure email sequences")
        print("   - Connect mailboxes to campaigns")
        
        if not self.domains and not self.mailboxes:
            print("\n⚡ QUICK START:")
            print("Run this script with options to configure your setup!")

def interactive_setup():
    """Interactive setup wizard"""
    helper = MailboxSetupHelper()
    
    print("🚀 Interactive Mailbox Setup Wizard")
    print("=" * 40)
    
    while True:
        print("\n📋 Options:")
        print("1. Add Domain")
        print("2. Add Mailbox") 
        print("3. Configure DNS for Domain")
        print("4. View Current Setup")
        print("5. Generate Setup Guide")
        print("6. Save & Exit")
        
        choice = input("\nChoose option (1-6): ").strip()
        
        if choice == '1':
            domain = input("Enter domain name (e.g., yourname-consulting.com): ").strip()
            registrar = input("Domain registrar (optional): ").strip()
            if domain:
                helper.add_domain(domain, registrar)
                
                # Generate DNS records
                dns_records = helper.generate_dns_records(domain)
                print(f"\n📋 Recommended DNS records for {domain}:")
                for record_type, record_value in dns_records.items():
                    if record_type != 'DKIM_NOTE':
                        print(f"  {record_type}: {record_value}")
                    else:
                        print(f"  Note: {record_value}")
        
        elif choice == '2':
            email = input("Enter email address (e.g., john@yourname-consulting.com): ").strip()
            provider = input("Email provider (zapmail/gmass/other): ").strip() or "zapmail"
            limit = input("Daily email limit (default: 30): ").strip()
            daily_limit = int(limit) if limit.isdigit() else 30
            
            if email and '@' in email:
                helper.add_mailbox(email, provider, daily_limit=daily_limit)
        
        elif choice == '3':
            if not helper.domains:
                print("❌ No domains configured. Add a domain first.")
                continue
                
            print("\nAvailable domains:")
            for i, domain in enumerate(helper.domains, 1):
                print(f"  {i}. {domain.domain}")
            
            try:
                domain_idx = int(input("Select domain number: ")) - 1
                if 0 <= domain_idx < len(helper.domains):
                    domain = helper.domains[domain_idx].domain
                    dns_records = helper.generate_dns_records(domain)
                    helper.update_domain_dns(domain, dns_records)
            except ValueError:
                print("Invalid selection")
        
        elif choice == '4':
            helper.print_setup_guide()
        
        elif choice == '5':
            checklist = helper.get_setup_checklist()
            print("\n📋 DETAILED SETUP CHECKLIST:")
            print(json.dumps(checklist, indent=2))
        
        elif choice == '6':
            helper.save_config()
            print("✅ Configuration saved! Next steps:")
            print("1. Configure your .env file with the mailbox details")
            print("2. Set up DNS records for your domains")
            print("3. Create mailboxes with your chosen provider")
            print("4. Configure Instantly campaigns")
            break
        
        else:
            print("Invalid option")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_setup()
    else:
        helper = MailboxSetupHelper()
        helper.print_setup_guide()
        
        print("\n💡 Run 'python mailbox_setup.py interactive' for guided setup")

if __name__ == "__main__":
    main()