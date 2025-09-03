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
from dataclasses import dataclass

# AI Provider imports
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Sheets imports (optional)
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

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
        self.setup_ai_provider()
        
    def setup_credentials(self):
        """Load API credentials from environment variables"""
        # AI Provider configuration
        self.ai_provider = os.getenv('AI_PROVIDER', 'claude').lower()
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
        
        # n8n workflow configuration
        self.n8n_webhook_url = os.getenv('N8N_ICEBREAKER_WEBHOOK_URL')
        
        # Azure OpenAI (optional)
        self.azure_openai_key = os.getenv('AZURE_OPENAI_KEY')
        self.azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.azure_openai_model = os.getenv('AZURE_OPENAI_MODEL', 'gpt-4')
        
        # Instantly (required for sending)
        self.instantly_api_key = os.getenv('INSTANTLY_API_KEY')
        self.instantly_workspace_id = os.getenv('INSTANTLY_WORKSPACE_ID')
        
        # Validate required credentials based on AI provider
        if self.ai_provider == 'claude':
            if self.n8n_webhook_url:
                logger.info("Using n8n workflow for Claude icebreaker generation")
            elif not self.claude_api_key:
                logger.warning("Neither Claude API key nor n8n webhook configured. AI icebreakers will use fallback templates.")
                self.ai_provider = 'none'
        elif self.ai_provider == 'azure_openai' and not all([self.azure_openai_key, self.azure_openai_endpoint]):
            logger.warning("Azure OpenAI credentials not found. AI icebreakers will use fallback templates.")
            self.ai_provider = 'none'
    
    def setup_instantly_client(self):
        """Initialize Instantly API client"""
        self.instantly_base_url = "https://api.instantly.ai/api/v1"
        if self.instantly_api_key:
            self.instantly_headers = {
                "Authorization": f"Bearer {self.instantly_api_key}",
                "Content-Type": "application/json"
            }
        else:
            logger.warning("Instantly API key not found. Email sending will be disabled.")
            self.instantly_headers = {}
    
    def setup_ai_provider(self):
        """Initialize the configured AI provider"""
        self.claude_client = None
        self.n8n_client = None
        
        if self.ai_provider == 'claude':
            # Try n8n workflow first, then direct API
            if self.n8n_webhook_url:
                try:
                    from n8n_icebreaker_client import N8nIcebreakerClient
                    self.n8n_client = N8nIcebreakerClient(self.n8n_webhook_url)
                    logger.info("n8n Claude workflow client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize n8n client: {e}")
                    logger.info("Falling back to direct Claude API...")
            
            # Direct Claude API (fallback or primary if no n8n)
            if not self.n8n_client and CLAUDE_AVAILABLE and self.claude_api_key:
                try:
                    self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                    logger.info("Claude API client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Claude client: {e}")
                    self.ai_provider = 'none'
            elif not self.n8n_client and not self.claude_api_key:
                logger.warning("No Claude configuration available")
                self.ai_provider = 'none'
        
        elif self.ai_provider == 'azure_openai' and OPENAI_AVAILABLE and self.azure_openai_key:
            try:
                openai.api_type = "azure"
                openai.api_base = self.azure_openai_endpoint
                openai.api_version = "2023-12-01-preview"
                openai.api_key = self.azure_openai_key
                logger.info("Azure OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI client: {e}")
                self.ai_provider = 'none'
        
        elif self.ai_provider != 'none':
            logger.warning(f"AI provider '{self.ai_provider}' not available or not configured. Using fallback templates.")
            self.ai_provider = 'none'
        
        logger.info(f"AI Provider: {self.ai_provider} (n8n: {bool(self.n8n_client)}, direct: {bool(self.claude_client)})")
    
    def get_column_mapping(self) -> Dict[str, str]:
        """
        Get column mapping for different data sources (Apollo, FindyLead, etc.)
        """
        # Default FindyLead mapping
        mapping = {
            'first_name': 'first_name',
            'last_name': 'last_name', 
            'email': 'email',
            'company_name': 'company_name',
            'industry': 'industry',
            'website': 'website',
            'title': 'title',
            'linkedin': 'linkedin'
        }
        
        # Apollo CSV mapping (common column names from Apollo exports)
        apollo_mapping = {
            'first_name': os.getenv('APOLLO_CSV_MAPPING_FIRST_NAME', 'first_name'),
            'last_name': os.getenv('APOLLO_CSV_MAPPING_LAST_NAME', 'last_name'),
            'email': os.getenv('APOLLO_CSV_MAPPING_EMAIL', 'email'),
            'company_name': os.getenv('APOLLO_CSV_MAPPING_COMPANY', 'company'),
            'industry': os.getenv('APOLLO_CSV_MAPPING_INDUSTRY', 'industry'),
            'website': os.getenv('APOLLO_CSV_MAPPING_WEBSITE', 'website_url'),
            'title': os.getenv('APOLLO_CSV_MAPPING_TITLE', 'title'),
            'linkedin': 'linkedin'
        }
        
        # Use Apollo mapping if configured
        data_source = os.getenv('DEFAULT_DATA_SOURCE', 'csv')
        if data_source in ['apollo_csv', 'apollo']:
            mapping.update(apollo_mapping)
        
        return mapping

    def detect_csv_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Auto-detect column names in CSV (helpful for Apollo exports)
        """
        columns = df.columns.str.lower().tolist()
        detected_mapping = {}
        
        # Common variations for each field
        field_variations = {
            'first_name': ['first_name', 'first name', 'firstname', 'fname', 'given_name'],
            'last_name': ['last_name', 'last name', 'lastname', 'lname', 'family_name', 'surname'],
            'email': ['email', 'email_address', 'email address', 'e_mail', 'mail'],
            'company_name': ['company_name', 'company name', 'company', 'organization', 'org'],
            'industry': ['industry', 'sector', 'vertical', 'business_type'],
            'website': ['website', 'website_url', 'web_site', 'url', 'domain', 'company_url'],
            'title': ['title', 'job_title', 'position', 'role', 'job title'],
            'linkedin': ['linkedin', 'linkedin_url', 'linkedin profile', 'li_profile']
        }
        
        for field, variations in field_variations.items():
            for variation in variations:
                if variation in columns:
                    detected_mapping[field] = variation
                    break
        
        logger.info(f"Auto-detected columns: {detected_mapping}")
        return detected_mapping

    def load_csv_data(self, csv_path: str) -> List[Lead]:
        """
        Load and parse CSV from any source (FindyLead, Apollo, custom export)
        Auto-detects column names and handles various formats
        """
        logger.info(f"Loading CSV data from: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"CSV loaded with {len(df)} rows and columns: {list(df.columns)}")
            
            # Use the common processing logic
            return self._process_dataframe_to_leads(df)
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def validate_lead(self, lead: Lead) -> bool:
        """Validate that a lead has minimum required data"""
        # Must have email and company name
        if not lead.email or '@' not in lead.email:
            return False
        if not lead.company_name or len(lead.company_name.strip()) < 2:
            return False
        # At least one name field should be present
        if not lead.first_name and not lead.last_name:
            return False
        return True
    
    def load_google_sheets_data(self, sheet_id: str = None, range_name: str = None) -> List[Lead]:
        """
        Load lead data from Google Sheets
        Requires service account credentials configured in .env
        """
        if not GOOGLE_SHEETS_AVAILABLE:
            raise ImportError("Google Sheets integration not available. Run: pip install gspread google-auth")
        
        # Get configuration from environment
        sheet_id = sheet_id or os.getenv('GOOGLE_SHEETS_ID')
        range_name = range_name or os.getenv('GOOGLE_SHEETS_RANGE', 'Sheet1!A:Z')
        service_account_file = os.getenv('GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE')
        
        if not sheet_id:
            raise ValueError("Google Sheets ID not provided. Set GOOGLE_SHEETS_ID in .env or pass as parameter.")
        
        if not service_account_file or not os.path.exists(service_account_file):
            raise ValueError("Google Sheets service account file not found. Check GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE in .env")
        
        logger.info(f"Loading data from Google Sheets: {sheet_id}")
        
        try:
            # Set up credentials
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)
            client = gspread.authorize(creds)
            
            # Open the spreadsheet
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.get_worksheet(0)  # First worksheet
            
            # Get all records as list of dictionaries
            records = worksheet.get_all_records()
            
            if not records:
                raise ValueError("No data found in Google Sheet")
            
            logger.info(f"Retrieved {len(records)} rows from Google Sheets")
            
            # Convert to DataFrame for consistent processing
            df = pd.DataFrame(records)
            
            # Use the same processing logic as CSV
            return self._process_dataframe_to_leads(df)
            
        except Exception as e:
            logger.error(f"Error loading Google Sheets data: {e}")
            raise
    
    def _process_dataframe_to_leads(self, df: pd.DataFrame) -> List[Lead]:
        """
        Common processing logic for DataFrame (from CSV or Google Sheets)
        """
        logger.info(f"Processing DataFrame with {len(df)} rows and columns: {list(df.columns)}")
        
        # Get column mapping (from config or auto-detect)
        mapping = self.get_column_mapping()
        detected = self.detect_csv_columns(df)
        
        # Use detected columns if available, fall back to config mapping
        final_mapping = {field: detected.get(field, mapping.get(field, '')) for field in mapping.keys()}
        
        logger.info(f"Using column mapping: {final_mapping}")
        
        leads = []
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Extract data using the mapping
                lead_data = {}
                for field, column_name in final_mapping.items():
                    if column_name and column_name in df.columns:
                        value = str(row.get(column_name, '')).strip()
                        # Clean up common data issues
                        if value.lower() in ['nan', 'none', 'null', '']:
                            value = ''
                        lead_data[field] = value
                
                lead = Lead(
                    first_name=lead_data.get('first_name', ''),
                    last_name=lead_data.get('last_name', ''),
                    email=lead_data.get('email', ''),
                    company_name=lead_data.get('company_name', ''),
                    industry=lead_data.get('industry', ''),
                    website=lead_data.get('website', ''),
                    title=lead_data.get('title', ''),
                    linkedin=lead_data.get('linkedin', '')
                )
                
                # Validate required fields
                if self.validate_lead(lead):
                    leads.append(lead)
                else:
                    skipped_count += 1
                    if skipped_count <= 5:  # Only log first few
                        logger.warning(f"Skipping invalid lead: email='{lead.email}', company='{lead.company_name}'")
            
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
                skipped_count += 1
        
        logger.info(f"Processed {len(leads)} valid leads, skipped {skipped_count} invalid entries")
        
        if len(leads) == 0:
            logger.error("No valid leads found! Check column mapping and data format.")
            raise ValueError("No valid leads found in data source")
        
        return leads
    
    def get_icebreaker_template(self) -> str:
        """Get icebreaker template from configuration"""
        default_template = "Love your approach to {specific_observation}, been following {company_name} for a while, big fan of your {service_focus}."
        return os.getenv('ICEBREAKER_TEMPLATE', default_template)
    
    def get_icebreaker_fallback(self, lead: Lead) -> str:
        """Get configured fallback icebreaker"""
        fallback_template = os.getenv('ICEBREAKER_FALLBACK', 
            "Impressed by what you're building at {company_name}, particularly your approach in the {industry} space.")
        
        return fallback_template.format(
            company_name=lead.company_name,
            industry=lead.industry or "business",
            first_name=lead.first_name
        )
    
    def generate_n8n_icebreaker(self, lead: Lead) -> str:
        """Generate icebreaker using n8n workflow"""
        if not self.n8n_client:
            logger.warning("n8n client not available, trying direct Claude API")
            return self.generate_claude_icebreaker(lead)
        
        try:
            # Convert Lead to n8n client Lead format
            from n8n_icebreaker_client import Lead as N8nLead
            n8n_lead = N8nLead(
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=lead.email,
                company_name=lead.company_name,
                industry=lead.industry,
                website=lead.website,
                title=lead.title
            )
            
            template = self.get_icebreaker_template()
            result = self.n8n_client.generate_icebreaker(n8n_lead, template)
            
            if result.get('status') == 'success':
                logger.info(f"Generated n8n icebreaker for {lead.company_name}: {result['icebreaker'][:50]}...")
                return result['icebreaker']
            elif result.get('status') == 'fallback':
                logger.warning(f"n8n workflow failed for {lead.company_name}: {result.get('error', 'Unknown error')}")
                return result['icebreaker']
            else:
                logger.error(f"Unexpected n8n response for {lead.company_name}: {result}")
                return self.get_icebreaker_fallback(lead)
                
        except Exception as e:
            logger.error(f"Error with n8n icebreaker for {lead.company_name}: {e}")
            return self.generate_claude_icebreaker(lead)

    def generate_claude_icebreaker(self, lead: Lead) -> str:
        """Generate icebreaker using direct Claude API"""
        if not self.claude_client:
            logger.warning("Claude client not available, using fallback")
            return self.get_icebreaker_fallback(lead)
        
        template = self.get_icebreaker_template()
        
        prompt = f"""You're an expert at writing personalized cold email icebreakers that convert. 

Write a 1-2 sentence icebreaker for this prospect:
- Company: {lead.company_name}
- Industry: {lead.industry}
- Contact: {lead.first_name} {lead.last_name}
- Title: {lead.title}
- Website: {lead.website}

The icebreaker should:
1. Sound like I've been casually following their company
2. Mention something specific about their business (not generic)
3. Be conversational and genuine (not corporate or salesy)
4. Focus on their expertise or business approach
5. Be under 25 words total
6. Follow this format: "{template}"

Generate ONLY the icebreaker text - no quotes, no explanations, just the personalized line."""

        try:
            message = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=100,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            icebreaker = message.content[0].text.strip()
            
            # Clean up common artifacts
            icebreaker = icebreaker.strip('"\'')
            if icebreaker.endswith('.'):
                icebreaker = icebreaker[:-1]
            
            logger.info(f"Generated Claude API icebreaker for {lead.company_name}: {icebreaker[:50]}...")
            return icebreaker
            
        except Exception as e:
            logger.error(f"Error generating Claude icebreaker for {lead.company_name}: {e}")
            return self.get_icebreaker_fallback(lead)
    
    def generate_openai_icebreaker(self, lead: Lead) -> str:
        """Generate icebreaker using Azure OpenAI"""
        template = self.get_icebreaker_template()
        
        prompt = f"""Generate a personalized 1-2 sentence icebreaker for a cold email to this prospect:
        
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
        6. Follow this general format: "{template}"
        
        Generate ONLY the icebreaker text, no quotes or explanations.
        Make it specific to this company and industry:"""
        
        try:
            response = openai.ChatCompletion.create(
                engine=self.azure_openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at writing personalized cold email icebreakers that convert. Focus on being specific and genuine."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            icebreaker = response.choices[0].message.content.strip()
            
            # Clean up common AI artifacts
            icebreaker = icebreaker.strip('"\'')
            if icebreaker.endswith('.'):
                icebreaker = icebreaker[:-1]
            
            logger.info(f"Generated OpenAI icebreaker for {lead.company_name}: {icebreaker[:50]}...")
            return icebreaker
            
        except Exception as e:
            logger.error(f"Error generating OpenAI icebreaker for {lead.company_name}: {e}")
            return self.get_icebreaker_fallback(lead)

    def generate_ai_icebreaker(self, lead: Lead) -> str:
        """
        Generate personalized icebreaker using configured AI provider
        Routes to Claude, Azure OpenAI, or fallback templates
        """
        # Check if icebreaker generation is enabled
        if not os.getenv('ICEBREAKER_ENABLED', 'true').lower() == 'true':
            logger.info("AI icebreaker generation disabled, using fallback")
            return self.get_icebreaker_fallback(lead)
        
        # Route to appropriate AI provider
        if self.ai_provider == 'claude':
            # Prefer n8n workflow if available, fallback to direct API
            if self.n8n_client:
                return self.generate_n8n_icebreaker(lead)
            else:
                return self.generate_claude_icebreaker(lead)
        elif self.ai_provider == 'azure_openai':
            return self.generate_openai_icebreaker(lead)
        else:
            logger.info(f"No AI provider configured ({self.ai_provider}), using fallback")
            return self.get_icebreaker_fallback(lead)
    
    def test_icebreaker_generation(self, num_tests: int = 3) -> List[str]:
        """Test icebreaker generation with sample data"""
        test_leads = [
            Lead("John", "Smith", "john@testcompany.com", "Test Marketing Agency", 
                 "Marketing", "https://testcompany.com", "CEO", ""),
            Lead("Jane", "Doe", "jane@consultech.com", "ConsuTech Solutions", 
                 "Consulting", "https://consultech.com", "Founder", ""),
            Lead("Bob", "Johnson", "bob@automate.co", "Automate Plus", 
                 "Automation", "https://automate.co", "CTO", "")
        ]
        
        results = []
        print(f"\nTesting icebreaker generation with {num_tests} samples...")
        
        for i, lead in enumerate(test_leads[:num_tests]):
            print(f"\nTest {i+1}: {lead.company_name}")
            icebreaker = self.generate_ai_icebreaker(lead)
            print(f"Result: {icebreaker}")
            results.append(icebreaker)
        
        return results
    
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
    print("Cold Email Lead Processor - Following Nick's Methodology")
    print("=" * 60)
    
    # Check for test mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Running in TEST MODE")
        try:
            processor = ColdEmailProcessor()
            processor.test_icebreaker_generation()
            return
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return
    
    # Initialize processor
    try:
        processor = ColdEmailProcessor()
        print("✅ Processor initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing processor: {e}")
        print("💡 Check your .env file configuration")
        return
    
    # Choose data source
    data_source = os.getenv('DEFAULT_DATA_SOURCE', 'csv')
    
    print(f"\n📊 Data Source Options:")
    print("1. CSV File (Apollo/FindyLead/Custom)")
    print("2. Google Sheets")
    print("3. Use default from .env")
    
    choice = input("Choose data source (1/2/3): ").strip()
    
    leads = []
    try:
        if choice == '2' or (choice == '3' and data_source == 'google_sheets'):
            # Google Sheets
            if not GOOGLE_SHEETS_AVAILABLE:
                print("❌ Google Sheets integration not available. Install with: pip install gspread google-auth")
                return
            
            sheet_id = input("Enter Google Sheets ID (or press Enter for .env default): ").strip()
            leads = processor.load_google_sheets_data(sheet_id if sheet_id else None)
            print(f"✅ Loaded {len(leads)} leads from Google Sheets")
            
        else:
            # CSV file (default)
            csv_path = input("Enter path to CSV file (Apollo/FindyLead/Custom): ").strip()
            if not csv_path:
                csv_path = "leads_export.csv"  # Default filename
            
            leads = processor.load_csv_data(csv_path)
            print(f"✅ Loaded {len(leads)} leads from CSV")
        
        if leads:
            print(f"📊 First lead preview: {leads[0].first_name} {leads[0].last_name} - {leads[0].company_name}")
            
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        print("💡 Check your configuration and data format")
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