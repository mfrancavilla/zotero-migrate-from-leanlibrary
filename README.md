# SciWheel-to-Zotero Hierarchical Migration Toolkit

This repository provides a reliable, two-part automated framework to migrate a massive reference library out of SciWheel and into Zotero while fully preserving:
1. Multi-level nested collection folder hierarchies (which standard .ris and .bib file exports flatten and destroy).
2. Local PDF attachments, safely cross-referenced, linked, and matched back to their respective database entries without duplication errors.

---

## The Migration Problem

When exporting references from SciWheel, the web platform completely detaches folders from documents or collapses nested collections into flat text labels hidden inside metadata tags (such as U1 blocks). Furthermore, mass-downloading thousands of associated PDFs is restricted by the platform to small manual batch packages. 

This toolkit solves those limitations using a Browser-Side Scraping/Automation Pipeline combined with a Local Python Data Engine that builds a custom RIS file embedding absolute local paths (L1) and hierarchy keys (DP).

---

## Step 1: Automated Batch PDF Exporter

SciWheel restricts PDF bulk-downloads to 25 items per page. The JavaScript automation script below runs directly in your browser console, reading dynamic DOM elements to calculate the total library volume, auto-naming zip batches sequentially (SciWheel_Batch_001.zip), waiting for the server to compile each package, and advancing pages automatically.

### Critical Browser Configuration
Before executing, prevent your browser from stopping the script with file-save confirmation popups:
* Go to Browser Settings > Downloads.
* Toggle OFF "Ask you where to save each file" / "Ask whether to open or save files".
* Force all downloads to point silently to your native system Downloads directory.

### Execution Script (auto_exporter.js)
Navigate to the first page of your reference list, open the Web Developer Console (F12 or Cmd + Option + K on macOS), paste this code, and hit Enter:

```javascript
(async function() {
    let startPage = 1; // Change this if resuming a disconnected session
    const DELAY_BETWEEN_STEPS = 1200; 

    console.log(`Starting dynamic SciWheel Auto-Exporter from page ${startPage}...`);
    const sleep = ms => new Promise(res => setTimeout(res, ms));

    async function waitForElement(selector, timeout = 10000) {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const el = document.querySelector(selector);
            if (el && el.getBoundingClientRect().width > 0) return el;
            await sleep(100);
        }
        return null;
    }

    let batchNum = startPage;
    let totalPages = batchNum;

    while (batchNum <= totalPages) {
        const counterEl = document.querySelector('span.counter.ng-binding');
        if (counterEl) {
            const parsedTotal = parseInt(counterEl.textContent.replace(/[^0-9]/g, ''), 10);
            if (!isNaN(parsedTotal) && parsedTotal > 0) totalPages = parsedTotal;
        }

        console.log(`=== PROCESSING BATCH ${batchNum} OF ${totalPages} ===`);

        const pageInput = document.querySelector('input[data-test-id="page-number"]');
        if (pageInput) {
            const currentUIDashboardPage = parseInt(pageInput.value, 10);
            if (currentUIDashboardPage !== batchNum) batchNum = currentUIDashboardPage;
        }

        console.log("Selecting all items on page...");
        const selectAllBtn = await waitForElement('.select-all');
        if (!selectAllBtn) break;
        
        if (selectAllBtn.classList.contains('none')) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        console.log("Opening Action Menu...");
        const actionMenuBtn = await waitForElement('[data-test-id="open-selected-refs-contextmenu-bttn"]');
        if (!actionMenuBtn) break;
        actionMenuBtn.click();
        await sleep(1500); 

        console.log("Clicking 'Download PDFs...' options panel...");
        const downloadOption = await waitForElement('[data-test-id="download-selected-refs-pdfs-bttn"]');
        if (!downloadOption) {
            let fallbackFound = false;
            const elements = document.querySelectorAll('li');
            for (const el of elements) {
                if (el.textContent.includes("Download PDFs")) {
                    el.click();
                    fallbackFound = true;
                    break;
                }
            }
            if (!fallbackFound) break;
        } else {
            downloadOption.click();
        }
        
        console.log("Waiting for Download Modal...");
        const nameInput = await waitForElement('input.mdc-textfield__input');
        if (!nameInput) break;

        const customFileName = `SciWheel_Batch_${String(batchNum).padStart(3, '0')}`;
        nameInput.value = customFileName;
        nameInput.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(800);

        const submitBtn = document.querySelector('button[ng-click="exportReferences()"]');
        console.log(`Triggering download package for: ${customFileName}`);
        submitBtn.click();
        await sleep(1500);

        console.log("SciWheel server compiling zip package. Waiting...");
        let attempts = 0;
        while (attempts < 90) { 
            const spans = Array.from(document.querySelectorAll('span'));
            const isPreparing = spans.some(el => el.textContent.includes("Preparing file for download"));
            if (!isPreparing) {
                console.log("Download dispatched successfully!");
                break;
            }
            await sleep(1000);
            attempts++;
        }

        await sleep(2500); 

        console.log("Deselecting current page items...");
        if (selectAllBtn && !selectAllBtn.classList.contains('none')) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        if (batchNum < totalPages) {
            console.log("Navigating forward to next page index...");
            const nextArrow = document.querySelector('[data-test-id="arrow-next-button"]');
            if (nextArrow && !nextArrow.classList.contains('is-disabled')) {
                nextArrow.click();
                await sleep(5000); 
                batchNum++;        
            } else {
                break;
            }
        } else {
            console.log("ALL BATCHES EXPORTED SUCCESSFULLY!");
            break;
        }
    }
})();
