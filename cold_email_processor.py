#!/usr/bin/env python3
"""
Cold Email Lead Processor - Following Nick's Methodology
Processes FindyLead CSV exports with AI personalization and Instantly integration
"""

import pandas as pd
import requests
import json
import time
import logging
from datetime import datetime
import os
from typing import Dict, List, Optional
import openai
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cold_email_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Lead:
    """Lead data structure"""
    first_name: str
    last_name: str
    email: str
    company_name: str
    industry: str
    website: str
    title: str = ""
    linkedin: str = ""
    
class ColdEmailProcessor:
    """Main processor for cold email automation following Nick's methodology"""
    
    def __init__(self):
        self.setup_credentials()
        self.setup_instantly_client()
        self.setup_openai_client()
        
    def setup_credentials(self):
        """Load API credentials from environment variables"""
        self.azure_openai_key = os.getenv('AZURE_OPENAI_KEY')
        self.azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.instantly_api_key = os.getenv('INSTANTLY_API_KEY')
        self.instantly_workspace_id = os.getenv('INSTANTLY_WORKSPACE_ID')
        
        if not all([self.azure_openai_key, self.azure_openai_endpoint, self.instantly_api_key]):
            raise ValueError("Missing required environment variables. Check .env file.")
    
    def setup_instantly_client(self):
        """Initialize Instantly API client"""
        self.instantly_base_url = "https://api.instantly.ai/api/v1"
        self.instantly_headers = {
            "Authorization": f"Bearer {self.instantly_api_key}",
            "Content-Type": "application/json"
        }
    
    def setup_openai_client(self):
        """Initialize Azure OpenAI client"""
        openai.api_type = "azure"
        openai.api_base = self.azure_openai_endpoint
        openai.api_version = "2023-12-01-preview"
        openai.api_key = self.azure_openai_key
    
    def load_findylead_csv(self, csv_path: str) -> List[Lead]:
        """
        Load and parse FindyLead CSV export
        Expected columns: first_name, last_name, email, company_name, industry, website
        """
        logger.info(f"Loading FindyLead CSV from: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            leads = []
            
            for _, row in df.iterrows():
                lead = Lead(
                    first_name=str(row.get('first_name', '')).strip(),
                    last_name=str(row.get('last_name', '')).strip(),
                    email=str(row.get('email', '')).strip(),
                    company_name=str(row.get('company_name', '')).strip(),
                    industry=str(row.get('industry', '')).strip(),
                    website=str(row.get('website', '')).strip(),
                    title=str(row.get('title', '')).strip(),
                    linkedin=str(row.get('linkedin', '')).strip()
                )
                
                # Basic validation
                if lead.email and lead.company_name and '@' in lead.email:
                    leads.append(lead)
                else:
                    logger.warning(f"Skipping invalid lead: {lead.email}")
            
            logger.info(f"Loaded {len(leads)} valid leads from CSV")
            return leads
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def generate_ai_icebreaker(self, lead: Lead) -> str:
        """
        Generate personalized icebreaker using Azure OpenAI
        Following Nick's methodology for AI personalization
        """
        prompt = f"""
        Generate a personalized 1-2 sentence icebreaker for a cold email to this prospect:
        
        Company: {lead.company_name}
        Industry: {lead.industry}
        Website: {lead.website}
        Contact: {lead.first_name} {lead.last_name}
        Title: {lead.title}
        
        The icebreaker should:
        1. Sound like I've been following their company
        2. Mention something specific about their business approach or services
        3. Be genuine and conversational (not salesy)
        4. Focus on their expertise or recent growth
        5. Be under 30 words total
        
        Example format: "Love your no-frills approach to [specific service], been following [company] for [timeframe], big fan of how you [specific observation]."
        
        Generate ONLY the icebreaker text, no quotes or explanations:
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine="gpt-4",  # Your deployed model name
                messages=[
                    {"role": "system", "content": "You are an expert at writing personalized cold email icebreakers that convert. Focus on being specific and genuine."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            icebreaker = response.choices[0].message.content.strip()
            logger.info(f"Generated icebreaker for {lead.company_name}: {icebreaker[:50]}...")
            return icebreaker
            
        except Exception as e:
            logger.error(f"Error generating icebreaker for {lead.company_name}: {e}")
            # Fallback to generic icebreaker
            return f"Love what you're building at {lead.company_name}, been following your growth in the {lead.industry} space."
    
    def calculate_lead_score(self, lead: Lead) -> int:
        """
        Calculate lead score to determine campaign assignment
        Following Nick's methodology for lead scoring
        """
        score = 0
        
        # Company size indicators
        if any(keyword in lead.company_name.lower() for keyword in ['agency', 'consulting', 'services']):
            score += 25
        
        # Industry scoring (service businesses score higher)
        high_value_industries = ['marketing', 'consulting', 'agency', 'services', 'legal', 'accounting']
        if any(industry in lead.industry.lower() for industry in high_value_industries):
            score += 30
        
        # Title scoring (decision makers)
        decision_maker_titles = ['owner', 'ceo', 'president', 'founder', 'director', 'vp']
        if any(title in lead.title.lower() for title in decision_maker_titles):
            score += 25
        
        # Website presence (indicates established business)
        if lead.website and 'http' in lead.website:
            score += 10
        
        # LinkedIn presence
        if lead.linkedin:
            score += 10
        
        return min(score, 100)  # Cap at 100
    
    def assign_campaign_by_score(self, score: int) -> str:
        """
        Assign Instantly campaign based on lead score
        Following Nick's methodology for campaign assignment
        """
        if score >= 80:
            return "enterprise-direct-pitch"  # High-value, direct approach
        elif score >= 60:
            return "professional-nurture"    # Medium-value, nurture first
        else:
            return "educational-sequence"    # Low-value, education first
    
    def create_instantly_lead(self, lead: Lead, icebreaker: str, campaign_id: str) -> bool:
        """
        Create lead in Instantly with personalized icebreaker
        """
        lead_data = {
            "leads": [{
                "email": lead.email,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "company_name": lead.company_name,
                "personalization": icebreaker,
                "custom_variables": {
                    "industry": lead.industry,
                    "website": lead.website,
                    "title": lead.title,
                    "icebreaker": icebreaker
                }
            }],
            "campaign_id": campaign_id,
            "skip_if_in_workspace": True
        }
        
        try:
            response = requests.post(
                f"{self.instantly_base_url}/lead/add",
                headers=self.instantly_headers,
                json=lead_data
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully added {lead.email} to campaign {campaign_id}")
                return True
            else:
                logger.error(f"Error adding lead {lead.email}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception adding lead {lead.email}: {e}")
            return False
    
    def get_instantly_campaigns(self) -> Dict:
        """Get available campaigns from Instantly"""
        try:
            response = requests.get(
                f"{self.instantly_base_url}/campaign/list",
                headers=self.instantly_headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting campaigns: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Exception getting campaigns: {e}")
            return {}
    
    def process_leads_batch(self, leads: List[Lead], batch_size: int = 50) -> Dict:
        """
        Process leads in batches following Nick's methodology
        Returns statistics on processing results
        """
        total_leads = len(leads)
        processed = 0
        successful = 0
        failed = 0
        
        stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'campaign_distribution': {
                'enterprise-direct-pitch': 0,
                'professional-nurture': 0,
                'educational-sequence': 0
            }
        }
        
        logger.info(f"Starting batch processing of {total_leads} leads")
        
        # Get available campaigns
        campaigns = self.get_instantly_campaigns()
        logger.info(f"Available campaigns: {list(campaigns.keys()) if campaigns else 'None found'}")
        
        # Process in batches to respect rate limits
        for i in range(0, total_leads, batch_size):
            batch = leads[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: leads {i+1} to {min(i+batch_size, total_leads)}")
            
            for lead in batch:
                try:
                    # Generate AI icebreaker
                    icebreaker = self.generate_ai_icebreaker(lead)
                    
                    # Calculate lead score
                    score = self.calculate_lead_score(lead)
                    
                    # Assign campaign
                    campaign_name = self.assign_campaign_by_score(score)
                    
                    # Create lead in Instantly
                    success = self.create_instantly_lead(lead, icebreaker, campaign_name)
                    
                    if success:
                        successful += 1
                        stats['campaign_distribution'][campaign_name] += 1
                    else:
                        failed += 1
                    
                    processed += 1
                    
                    # Rate limiting - respect API limits
                    time.sleep(0.5)  # 2 requests per second max
                    
                except Exception as e:
                    logger.error(f"Error processing lead {lead.email}: {e}")
                    failed += 1
                    processed += 1
            
            # Longer pause between batches
            if i + batch_size < total_leads:
                logger.info("Pausing between batches...")
                time.sleep(2)
        
        stats['total_processed'] = processed
        stats['successful'] = successful
        stats['failed'] = failed
        
        logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        return stats
    
    def generate_processing_report(self, stats: Dict, output_file: str = None):
        """Generate processing report"""
        report = f"""
Cold Email Lead Processing Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PROCESSING STATISTICS:
- Total Leads Processed: {stats['total_processed']}
- Successfully Added: {stats['successful']}
- Failed: {stats['failed']}
- Success Rate: {(stats['successful']/stats['total_processed']*100):.1f}%

CAMPAIGN DISTRIBUTION:
- Enterprise Direct Pitch: {stats['campaign_distribution']['enterprise-direct-pitch']} leads
- Professional Nurture: {stats['campaign_distribution']['professional-nurture']} leads  
- Educational Sequence: {stats['campaign_distribution']['educational-sequence']} leads

EXPECTED PERFORMANCE (Based on Nick's Metrics):
- Expected Reply Rate: 1-2%
- Expected Positive Replies: {int(stats['successful'] * 0.01)} - {int(stats['successful'] * 0.02)}
- Expected Meetings: {int(stats['successful'] * 0.007)} - {int(stats['successful'] * 0.013)}

Next Steps:
1. Monitor campaign performance in Instantly dashboard
2. Track replies and engagement over next 7 days
3. Optimize sequences based on initial results
4. Scale successful campaigns
        """
        
        print(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_file}")

def main():
    """Main execution function"""
    print("🚀 Cold Email Lead Processor - Following Nick's Methodology")
    print("=" * 60)
    
    # Initialize processor
    try:
        processor = ColdEmailProcessor()
        print("✅ Processor initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing processor: {e}")
        return
    
    # Load leads from CSV
    csv_path = input("Enter path to FindyLead CSV file: ").strip()
    if not csv_path:
        csv_path = "findylead_export.csv"  # Default filename
    
    try:
        leads = processor.load_findylead_csv(csv_path)
        print(f"✅ Loaded {len(leads)} leads from CSV")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return
    
    # Confirm processing
    print(f"\nReady to process {len(leads)} leads with AI personalization")
    confirm = input("Continue? (y/n): ").lower().strip()
    
    if confirm != 'y':
        print("❌ Processing cancelled")
        return
    
    # Process leads
    print("\n🔄 Starting lead processing...")
    stats = processor.process_leads_batch(leads)
    
    # Generate report
    print("\n📊 Generating final report...")
    report_file = f"cold_email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    processor.generate_processing_report(stats, report_file)
    
    print("\n🎉 Processing complete! Check Instantly dashboard for campaign status.")

if __name__ == "__main__":
    main()