# Bridging Brain v4 - AI-Powered Lender Matching

An intelligent bridging finance assistant that combines structured knockout filters with AI-powered conversation to help brokers find the best lenders for complex deals.

## Features

- **Hybrid Architecture**: Structured deal essentials for hard knockouts + AI conversation for nuanced analysis
- **65+ Lenders**: Comprehensive database with 113 data points per lender
- **Intelligent Questions**: AI asks relevant follow-up questions based on deal characteristics
- **Smart Recommendations**: Ranked lender suggestions with explanations and trade-offs
- **Actionable Outputs**: Draft enquiry emails and phone call checklists
- **Feedback Learning**: System improves based on broker feedback
- **Theme Options**: Multiple UI themes (Midnight, Daylight, Navy, Forest)

## Quick Start

### Windows
1. Double-click `START.bat`
2. Open http://127.0.0.1:8000 in your browser

### Mac/Linux
1. Run `chmod +x start.sh && ./start.sh`
2. Open http://127.0.0.1:8000 in your browser

## AI Setup (Optional but Recommended)

To enable AI features, you need an Anthropic API key:

1. Sign up at https://console.anthropic.com/
2. Create an API key
3. Set the environment variable:
   - Windows: `set ANTHROPIC_API_KEY=your-key-here`
   - Mac/Linux: `export ANTHROPIC_API_KEY=your-key-here`
4. Restart the application

**Cost**: Approximately £0.02-0.05 per query using Claude Sonnet.

## How to Use

1. **Fill in Deal Essentials** (left panel):
   - Loan amount required
   - Purchase price (if applicable)
   - Market value
   - Property type & geography
   - Entity type
   - Regulated/Refurb toggles

2. **Chat with the AI** (right panel):
   - Describe your deal in natural language
   - Answer the AI's clarifying questions
   - Receive ranked lender recommendations
   - Get draft emails and call checklists

3. **Provide Feedback**:
   - After using a lender, submit feedback
   - This helps improve future recommendations

## Files

- `main.py` - Backend API server
- `index.html` - Frontend UI
- `script.js` - Frontend logic
- `ontology.py` - Domain knowledge for AI
- `setup_database.py` - Database import script
- `lenders.db` - SQLite database (created on first run)

## Tech Stack

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **AI**: Claude Sonnet (Anthropic API)

## Updating Lender Data

1. Export your questionnaire responses to Excel
2. Replace `Bridging_Lenders_Questionnaire_Responses_1.xlsx`
3. Delete `lenders.db`
4. Restart the application (database will be recreated)

## Support

For issues or suggestions, contact the development team.

---

Built with 🧠 by Bridging Brain
