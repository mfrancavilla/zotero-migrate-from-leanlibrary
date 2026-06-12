/**
 * SciWheel Auto-Exporter
 * * Run this script directly in the Firefox Web Developer Console on your 
 * SciWheel reference dashboard. It will automatically step page-by-page, 
 * select all items, bundle them into uniquely named zip archives, 
 * and advance through your entire library.
 */

(async function() {
    // === CONFIGURATION ===
    let startPage = 1; // Set this to your current page if resuming a disconnected session
    const DELAY_BETWEEN_STEPS = 1200; 

    console.log(`🚀 Starting dynamic SciWheel Auto-Exporter from page ${startPage}...`);

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
        // 1. Dynamic Total Page Discovery
        const counterEl = document.querySelector('span.counter.ng-binding');
        if (counterEl) {
            const parsedTotal = parseInt(counterEl.textContent.replace(/[^0-9]/g, ''), 10);
            if (!isNaN(parsedTotal) && parsedTotal > 0) {
                totalPages = parsedTotal;
            }
        }

        console.log(`\n==================================================\n💎 PROCESSING BATCH ${batchNum} OF ${totalPages}\n==================================================\n`);

        // 2. Cross-verify actual dashboard page input tracking
        const pageInput = document.querySelector('input[data-test-id="page-number"]');
        if (pageInput) {
            const currentUIDashboardPage = parseInt(pageInput.value, 10);
            console.log(`📄 SciWheel Dashboard actively tracking page: ${currentUIDashboardPage}`);
            if (currentUIDashboardPage !== batchNum) {
                console.warn(`⚠️ Sync Warning: Loop expected ${batchNum}, but DOM shows ${currentUIDashboardPage}. Syncing tracking index.`);
                batchNum = currentUIDashboardPage;
            }
        }

        // 3. Select All 25 items on the current page
        console.log("➡️ Selecting all items on page...");
        const selectAllBtn = await waitForElement('.select-all');
        if (!selectAllBtn) {
            console.error("❌ Could not find Select All button. Stopping script.");
            break;
        }
        
        if (selectAllBtn.classList.contains('none')) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        // 4. Click the Action Menu Button
        console.log("➡️ Opening Action Menu...");
        const actionMenuBtn = await waitForElement('[data-test-id="open-selected-refs-contextmenu-bttn"]');
        if (!actionMenuBtn) {
            console.error("❌ Action menu button hidden or disabled.");
            break;
        }
        actionMenuBtn.click();
        await sleep(1500); // UI open animation buffer

        // 5. Click 'Download PDFs...' option
        console.log("➡️ Clicking 'Download PDFs...' options panel...");
        const downloadOption = await waitForElement('[data-test-id="download-selected-refs-pdfs-bttn"]');
        if (!downloadOption) {
            console.warn("⚠️ Strict test ID missing, falling back to text scanning...");
            let fallbackFound = false;
            const elements = document.querySelectorAll('li');
            for (const el of elements) {
                if (el.textContent.includes("Download PDFs")) {
                    el.click();
                    fallbackFound = true;
                    break;
                }
            }
            if (!fallbackFound) {
                console.error("❌ Could not locate the Download PDFs item.");
                break;
            }
        } else {
            downloadOption.click();
        }
        
        // 6. Interact with the file naming modal box
        console.log("➡️ Waiting for Download Modal to overlay...");
        const nameInput = await waitForElement('input.mdc-textfield__input');
        if (!nameInput) {
            console.error("❌ Naming overlay modal timeout.");
            break;
        }

        const customFileName = `SciWheel_Batch_${String(batchNum).padStart(3, '0')}`;
        nameInput.value = customFileName;
        nameInput.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(800);

        // 7. Click the final submit "Download file" confirmation button
        const submitBtn = document.querySelector('button[ng-click="exportReferences()"]');
        console.log(`💾 Triggering download package for: ${customFileName}`);
        submitBtn.click();
        await sleep(1500);

        // 8. Loop check: Wait for server processing states to clear
        console.log("⏳ SciWheel server compiling zip package. Waiting...");
        let attempts = 0;
        let isDoneProcessing = false;
        while (attempts < 90) { 
            const spans = Array.from(document.querySelectorAll('span'));
            const isPreparing = spans.some(el => el.textContent.includes("Preparing file for download"));
            
            if (!isPreparing) {
                console.log("✅ Download dispatched successfully!");
                isDoneProcessing = true;
                break;
            }
            await sleep(1000);
            attempts++;
        }

        await sleep(2500); // Browser downloading pipe clearance buffer

        // 9. Uncheck Select All
        console.log("➡️ Deselecting current page items...");
        if (selectAllBtn && (selectAllBtn.classList.contains('is-half-checked') || !selectAllBtn.classList.contains('none'))) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        // 10. Advance to next page block layout
        if (batchNum < totalPages) {
            console.log("➡️ Navigating forward to next page index...");
            const nextArrow = document.querySelector('[data-test-id="arrow-next-button"]');
            
            if (nextArrow && !nextArrow.classList.contains('is-disabled')) {
                nextArrow.click();
                await sleep(5000); // Long wait for Angular DOM wipe execution
                batchNum++;        // Increment loop tracker safely after click succeeds
            } else {
                console.warn("⚠️ Next page arrow button reported as disabled ahead of target page limit count.");
                break;
            }
        } else {
            console.log(`\n==================================================\n🎉 ALL BATCHES EXPORTED SUCCESSFULLY!\n==================================================\n`);
            break;
        }
    }
})();
