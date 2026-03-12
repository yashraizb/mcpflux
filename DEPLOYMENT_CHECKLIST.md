# Deployment Checklist

## Pre-Deployment

- [ ] Python 3.9+ installed
- [ ] pip or uv package manager available
- [ ] OpenAI API account created
- [ ] OpenAI API key generated and available
- [ ] Virtual environment created (recommended)

## Installation Checklist

- [ ] Dependencies installed: `pip install -r spreadsheet_mcp_agent/requirements.txt`
- [ ] OPENAI_API_KEY environment variable set
- [ ] Server starts without errors: `python main.py`
- [ ] Server can be stopped with Ctrl+C
- [ ] No import errors in the console

## Testing Checklist

- [ ] Example data created: `python generate_examples.py`
- [ ] Sample CSV files generated (sales_data.csv, customer_data.csv)
- [ ] Manual query test successful
- [ ] Error handling verified (test with invalid file)
- [ ] Retry mechanism tested (intentionally trigger an error)

## Claude Desktop Integration Checklist

- [ ] Found Claude configuration file location
- [ ] Backed up original configuration file
- [ ] Added mcpServers section with spreadsheet_agent
- [ ] Used absolute path to main.py
- [ ] Set OPENAI_API_KEY in env section
- [ ] JSON syntax validated (no errors)
- [ ] Claude Desktop fully restarted
- [ ] Server appears in Claude's tools menu
- [ ] Test query successful in Claude

## Code Quality Checklist

- [ ] All modules import successfully
- [ ] No Python syntax errors
- [ ] Type hints present on all public functions
- [ ] Docstrings on all public functions
- [ ] Error messages are meaningful
- [ ] Logging configured and working
- [ ] Configuration values centralized
- [ ] No hardcoded values (except in config.py)

## Documentation Checklist

- [ ] README.md reviewed and accurate
- [ ] SETUP.md follows installation steps correctly
- [ ] CLAUDE_INTEGRATION.md provides clear instructions
- [ ] QUICK_REFERENCE.md has useful examples
- [ ] All code has docstrings
- [ ] Example queries provided
- [ ] Troubleshooting section completed

## Performance Checklist

- [ ] Server startup time < 2 seconds
- [ ] Query response time 2-6 seconds typical
- [ ] Error recovery works within timeout
- [ ] Memory usage reasonable for dataset size
- [ ] Large files (>100K rows) handled

## Security Checklist

- [ ] API key not in version control
- [ ] .env file excluded from git
- [ ] Configuration file has restricted permissions (macOS)
- [ ] No sensitive data logged
- [ ] Error messages don't expose system paths
- [ ] Only necessary environment variables exposed

## Functionality Checklist

### File Loading

- [ ] CSV files load correctly
- [ ] Excel files load correctly
- [ ] Unsupported formats rejected
- [ ] Empty files handled gracefully
- [ ] Large files (>1GB) work (or warn appropriately)

### Schema Extraction

- [ ] Column names extracted
- [ ] Data types identified
- [ ] Sample rows included (5)
- [ ] Row count accurate
- [ ] Schema formatted for LLM

### SQL Generation

- [ ] Natural language converted to SQL
- [ ] Table name "data" used
- [ ] Valid SQL generated
- [ ] No markdown in output
- [ ] Comments/explanations removed

### SQL Execution

- [ ] SQL executes on DataFrame
- [ ] Results returned correctly
- [ ] Column types preserved
- [ ] Large result sets handled (with limit)
- [ ] NULL values handled

### Error Recovery

- [ ] Invalid SQL caught
- [ ] LLM corrects SQL on retry
- [ ] Retries up to 3 times
- [ ] Clear error message on final failure
- [ ] Logs show recovery attempts

### Response Format

- [ ] JSON format valid
- [ ] Success flag accurate
- [ ] Generated SQL included
- [ ] Result preview shows first rows
- [ ] Row count accurate
- [ ] Column count accurate

## Example Queries Checklist

Test these queries:

- [ ] "What is the total revenue?" → Works
- [ ] "Top 5 products" → Works
- [ ] "Revenue by country" → Works
- [ ] "Average sales" → Works
- [ ] "How many records?" → Works
- [ ] Invalid syntax → Clear error message
- [ ] Non-existent column → Recovery or clear error

## Deployment Readiness

- [ ] All above items checked ✓
- [ ] Code reviewed and approved
- [ ] Documentation complete
- [ ] No debug statements remaining
- [ ] Logging configured for production
- [ ] Error handling comprehensive
- [ ] Configuration externalized
- [ ] Secrets not in code

## Going Live

1. **Production Environment Setup**
   - [ ] Python 3.9+ installed on production
   - [ ] Virtual environment created
   - [ ] Dependencies installed
   - [ ] Environment variables configured

2. **Server Deployment**
   - [ ] Code copied to production location
   - [ ] Permissions set correctly
   - [ ] main.py is executable (if needed)
   - [ ] Startup script created (optional)

3. **Claude Integration**
   - [ ] Configuration file updated
   - [ ] Absolute path set correctly
   - [ ] API key configured
   - [ ] Claude Desktop restarted

4. **Monitoring**
   - [ ] Logs being captured
   - [ ] Error alerts configured
   - [ ] Performance monitored
   - [ ] API usage monitored

5. **User Communication**
   - [ ] Users informed of availability
   - [ ] Usage documentation provided
   - [ ] Support contact provided
   - [ ] FAQ prepared

## Rollback Plan

If issues arise:

1. [ ] Stop the server: `Ctrl+C` in terminal
2. [ ] Remove from Claude config if needed
3. [ ] Restart Claude Desktop
4. [ ] Revert to previous version if necessary
5. [ ] Contact support if needed

## Maintenance

Regular tasks:

- [ ] Monitor API usage and costs
- [ ] Review logs for errors
- [ ] Update dependencies (monthly)
- [ ] Test with new data types
- [ ] Collect user feedback
- [ ] Plan improvements

## Sign-Off

- **Developer**: ********\_\_\_******** Date: **\_\_\_**
- **QA/Tester**: ********\_\_******** Date: **\_\_\_**
- **Deployment Lead**: ******\_****** Date: **\_\_\_**

---

## Quick Command Reference

```bash
# Installation
pip install -r spreadsheet_mcp_agent/requirements.txt

# Testing
python generate_examples.py
python spreadsheet_mcp_agent/example.py

# Running
python main.py

# Checking dependencies
pip freeze | grep -E "mcp|duckdb|pandas"

# Viewing logs
python main.py 2>&1 | tee server.log
```

## Contact & Support

For issues or questions:

1. Check QUICK_REFERENCE.md
2. Review SETUP.md
3. Check error logs
4. Consult code documentation

---

**Status**: ☐ Ready for Production
