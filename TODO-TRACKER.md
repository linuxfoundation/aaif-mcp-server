# TODO Tracker

This document tracks all TODO and FIXME comments from the source code. Items are organized by file and include line numbers for reference.

## src/aaif_mcp_server/tools/compliance.py

### Lines 46-48: Descartes Screening Field Integration
**Priority:** Production Phase
**Status:** Pending SFDC Sandbox Connection

Once the SFDC sandbox is connected, read the actual Descartes screening result field (e.g., `Screening_Status__c`, `Descartes_Result__c`). Currently returns clear status since Descartes handles sanctions screening at membership intake in Salesforce.

**Related Code:**
- `check_sanctions()` function
- SFDC/Descartes integration point
- Requires field name confirmation during sandbox validation

---

## Summary

**Total TODOs:** 1
**Total FIXMEs:** 0
**Total Items:** 1

### By Category
- Production/API Integration: 1
