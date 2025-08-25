#!/usr/bin/env python3
"""
Email Performance Monitor - Following Nick's Analytics Approach
Monitors Instantly campaigns and analyzes performance metrics
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List
import os
import openai
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CampaignMetrics:
    """Campaign performance metrics"""
    campaign_name: str
    total_sent: int
    delivered: int
    opened: int
    clicked: int
    replied: int
    bounced: int
    unsubscribed: int
    positive_replies: int = 0
    negative_replies: int = 0
    neutral_replies: int = 0

class EmailPerformanceMonitor:
    """Monitor email campaign performance following Nick's methodology"""
    
    def __init__(self):
        self.setup_credentials()
        self.setup_clients()
    
    def setup_credentials(self):
        """Load API credentials"""
        self.instantly_api_key = os.getenv('INSTANTLY_API_KEY')
        self.instantly_workspace_id = os.getenv('INSTANTLY_WORKSPACE_ID')
        self.azure_openai_key = os.getenv('AZURE_OPENAI_KEY')
        self.azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')  # Optional
        
        if not self.instantly_api_key:
            raise ValueError("INSTANTLY_API_KEY environment variable required")
    
    def setup_clients(self):
        """Initialize API clients"""
        self.instantly_base_url = "https://api.instantly.ai/api/v1"
        self.instantly_headers = {
            "Authorization": f"Bearer {self.instantly_api_key}",
            "Content-Type": "application/json"
        }
        
        # Setup OpenAI for reply analysis
        if self.azure_openai_key:
            openai.api_type = "azure"
            openai.api_base = self.azure_openai_endpoint
            openai.api_version = "2023-12-01-preview"
            openai.api_key = self.azure_openai_key
    
    def get_campaign_stats(self, campaign_id: str = None) -> List[CampaignMetrics]:
        """Get campaign statistics from Instantly"""
        try:
            url = f"{self.instantly_base_url}/analytics/campaign"
            if campaign_id:
                url += f"?campaign_id={campaign_id}"
            
            response = requests.get(url, headers=self.instantly_headers)
            
            if response.status_code == 200:
                data = response.json()
                campaigns = []
                
                for campaign_data in data.get('campaigns', []):
                    metrics = CampaignMetrics(
                        campaign_name=campaign_data.get('name', 'Unknown'),
                        total_sent=campaign_data.get('sent', 0),
                        delivered=campaign_data.get('delivered', 0),
                        opened=campaign_data.get('opened', 0),
                        clicked=campaign_data.get('clicked', 0),
                        replied=campaign_data.get('replied', 0),
                        bounced=campaign_data.get('bounced', 0),
                        unsubscribed=campaign_data.get('unsubscribed', 0)
                    )
                    campaigns.append(metrics)
                
                return campaigns
            else:
                logger.error(f"Error getting campaign stats: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Exception getting campaign stats: {e}")
            return []
    
    def get_recent_replies(self, hours_back: int = 24) -> List[Dict]:
        """Get recent email replies for analysis"""
        try:
            # Calculate timestamp
            since = datetime.now() - timedelta(hours=hours_back)
            timestamp = int(since.timestamp())
            
            response = requests.get(
                f"{self.instantly_base_url}/lead/replies?since={timestamp}",
                headers=self.instantly_headers
            )
            
            if response.status_code == 200:
                return response.json().get('replies', [])
            else:
                logger.error(f"Error getting replies: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Exception getting replies: {e}")
            return []
    
    def analyze_reply_sentiment(self, reply_text: str) -> str:
        """
        Analyze reply sentiment using AI
        Returns: 'positive', 'negative', or 'neutral'
        """
        if not self.azure_openai_key:
            return 'neutral'  # Fallback if no OpenAI
        
        prompt = f"""
        Analyze this email reply and categorize it as positive, negative, or neutral for sales purposes:
        
        Reply: "{reply_text}"
        
        Positive = Interested, asking questions, wants to learn more, scheduling meetings
        Negative = Not interested, unsubscribe requests, harsh rejections  
        Neutral = Out of office, general acknowledgment, unclear intent
        
        Respond with only one word: positive, negative, or neutral
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing sales email replies for sentiment."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            sentiment = response.choices[0].message.content.strip().lower()
            return sentiment if sentiment in ['positive', 'negative', 'neutral'] else 'neutral'
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 'neutral'
    
    def process_replies_with_ai(self, replies: List[Dict]) -> Dict:
        """Process replies with AI sentiment analysis"""
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        hot_leads = []
        
        for reply in replies:
            reply_text = reply.get('content', '')
            email = reply.get('email', '')
            campaign = reply.get('campaign_name', '')
            
            sentiment = self.analyze_reply_sentiment(reply_text)
            sentiment_counts[sentiment] += 1
            
            # Identify hot leads (positive replies)
            if sentiment == 'positive':
                hot_leads.append({
                    'email': email,
                    'campaign': campaign,
                    'reply': reply_text[:200] + '...' if len(reply_text) > 200 else reply_text,
                    'timestamp': reply.get('timestamp', '')
                })
        
        return {
            'sentiment_counts': sentiment_counts,
            'hot_leads': hot_leads,
            'total_replies': len(replies)
        }
    
    def calculate_nick_metrics(self, campaigns: List[CampaignMetrics]) -> Dict:
        """
        Calculate key metrics following Nick's methodology
        Focus on reply rates, positive reply rates, and meeting potential
        """
        total_sent = sum(c.total_sent for c in campaigns)
        total_delivered = sum(c.delivered for c in campaigns)
        total_opened = sum(c.opened for c in campaigns)
        total_clicked = sum(c.clicked for c in campaigns)
        total_replied = sum(c.replied for c in campaigns)
        total_bounced = sum(c.bounced for c in campaigns)
        
        # Calculate key Nick metrics
        metrics = {
            'total_sent': total_sent,
            'delivery_rate': (total_delivered / total_sent * 100) if total_sent > 0 else 0,
            'open_rate': (total_opened / total_delivered * 100) if total_delivered > 0 else 0,
            'click_rate': (total_clicked / total_delivered * 100) if total_delivered > 0 else 0,
            'reply_rate': (total_replied / total_delivered * 100) if total_delivered > 0 else 0,
            'bounce_rate': (total_bounced / total_sent * 100) if total_sent > 0 else 0,
        }
        
        # Nick's key benchmark: 1-2% reply rate target
        metrics['nick_benchmark_status'] = 'Good' if metrics['reply_rate'] >= 1.0 else 'Needs Improvement'
        
        # Estimate meetings based on Nick's 1 meeting per 150 emails formula
        metrics['estimated_meetings'] = int(total_delivered / 150 * (metrics['reply_rate'] / 100))
        
        return metrics
    
    def send_slack_notification(self, hot_leads: List[Dict]):
        """Send Slack notification for hot leads"""
        if not self.slack_webhook_url or not hot_leads:
            return
        
        message = {
            "text": f"🔥 {len(hot_leads)} Hot Leads Detected!",
            "attachments": []
        }
        
        for lead in hot_leads[:5]:  # Show top 5 hot leads
            attachment = {
                "color": "good",
                "fields": [
                    {"title": "Email", "value": lead['email'], "short": True},
                    {"title": "Campaign", "value": lead['campaign'], "short": True},
                    {"title": "Reply", "value": lead['reply'], "short": False}
                ]
            }
            message["attachments"].append(attachment)
        
        try:
            requests.post(self.slack_webhook_url, json=message)
            logger.info(f"Sent Slack notification for {len(hot_leads)} hot leads")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def generate_performance_report(self, campaigns: List[CampaignMetrics], reply_analysis: Dict, metrics: Dict) -> str:
        """Generate comprehensive performance report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""
🎯 COLD EMAIL PERFORMANCE REPORT
Generated: {timestamp}
Following Nick's Methodology

📊 OVERALL METRICS:
• Total Sent: {metrics['total_sent']:,}
• Delivery Rate: {metrics['delivery_rate']:.1f}%
• Open Rate: {metrics['open_rate']:.1f}%
• Click Rate: {metrics['click_rate']:.1f}%
• Reply Rate: {metrics['reply_rate']:.1f}%
• Bounce Rate: {metrics['bounce_rate']:.1f}%

🎯 NICK'S BENCHMARKS:
• Target Reply Rate: 1-2%
• Current Status: {metrics['nick_benchmark_status']}
• Estimated Meetings: {metrics['estimated_meetings']} (based on Nick's 1:150 formula)

💬 REPLY ANALYSIS (Last 24h):
• Total Replies: {reply_analysis['total_replies']}
• Positive Replies: {reply_analysis['sentiment_counts']['positive']} 🟢
• Negative Replies: {reply_analysis['sentiment_counts']['negative']} 🔴  
• Neutral Replies: {reply_analysis['sentiment_counts']['neutral']} ⚪

📈 CAMPAIGN BREAKDOWN:
"""
        
        for campaign in campaigns:
            if campaign.total_sent > 0:
                campaign_reply_rate = (campaign.replied / campaign.delivered * 100) if campaign.delivered > 0 else 0
                report += f"""
• {campaign.campaign_name}:
  - Sent: {campaign.total_sent} | Delivered: {campaign.delivered}
  - Opened: {campaign.opened} | Replied: {campaign.replied}
  - Reply Rate: {campaign_reply_rate:.1f}%
"""
        
        # Hot leads section
        if reply_analysis['hot_leads']:
            report += f"\n🔥 HOT LEADS ({len(reply_analysis['hot_leads'])}):\n"
            for i, lead in enumerate(reply_analysis['hot_leads'][:10], 1):
                report += f"{i}. {lead['email']} - {lead['campaign']}\n"
        
        # Recommendations based on Nick's methodology
        report += f"""
🚀 OPTIMIZATION RECOMMENDATIONS:
"""
        
        if metrics['reply_rate'] < 1.0:
            report += "• Reply rate below 1% - Consider improving subject lines and personalization\n"
        
        if metrics['delivery_rate'] < 95:
            report += "• Delivery rate low - Check domain reputation and email authentication\n"
        
        if metrics['open_rate'] < 20:
            report += "• Open rate low - Test new subject line variations\n"
        
        if reply_analysis['sentiment_counts']['positive'] > 0:
            report += f"• {reply_analysis['sentiment_counts']['positive']} positive replies - Follow up within 24 hours!\n"
        
        report += f"""
📋 NEXT ACTIONS:
1. Follow up with {len(reply_analysis['hot_leads'])} hot leads immediately
2. {"Scale successful campaigns" if metrics['reply_rate'] >= 1.0 else "Optimize underperforming campaigns"}
3. Monitor deliverability metrics daily
4. A/B test subject lines for campaigns below 1% reply rate

Report generated by Cold Email Performance Monitor
Following Nick's proven methodology for cold email success
        """
        
        return report
    
    def run_monitoring_cycle(self):
        """Run complete monitoring cycle"""
        logger.info("Starting email performance monitoring cycle")
        
        # Get campaign stats
        campaigns = self.get_campaign_stats()
        logger.info(f"Retrieved stats for {len(campaigns)} campaigns")
        
        # Get recent replies
        replies = self.get_recent_replies(24)  # Last 24 hours
        logger.info(f"Retrieved {len(replies)} recent replies")
        
        # Analyze replies with AI
        reply_analysis = self.process_replies_with_ai(replies)
        logger.info(f"Analyzed replies: {reply_analysis['sentiment_counts']}")
        
        # Calculate Nick's metrics
        metrics = self.calculate_nick_metrics(campaigns)
        
        # Send hot lead notifications
        if reply_analysis['hot_leads']:
            self.send_slack_notification(reply_analysis['hot_leads'])
        
        # Generate and save report
        report = self.generate_performance_report(campaigns, reply_analysis, metrics)
        
        # Save report to file
        report_filename = f"email_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(report)
        logger.info(f"Performance report saved to: {report_filename}")
        
        return {
            'campaigns': campaigns,
            'metrics': metrics,
            'reply_analysis': reply_analysis,
            'report_file': report_filename
        }

def main():
    """Main execution function"""
    print("📊 Email Performance Monitor - Following Nick's Analytics")
    print("=" * 60)
    
    try:
        monitor = EmailPerformanceMonitor()
        print("✅ Monitor initialized successfully")
        
        # Run monitoring cycle
        results = monitor.run_monitoring_cycle()
        
        print(f"\n🎉 Monitoring complete!")
        print(f"📋 Report saved to: {results['report_file']}")
        
        if results['reply_analysis']['hot_leads']:
            print(f"🔥 {len(results['reply_analysis']['hot_leads'])} hot leads require immediate follow-up!")
        
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        logger.error(f"Monitoring error: {e}")

if __name__ == "__main__":
    main()