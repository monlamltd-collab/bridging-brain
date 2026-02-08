/**
 * Bridging Brain v4 - Complete Frontend
 * Progressive Filtering Funnel: Left Brain (Coarse) → Middle Brain (Refiners) → Right Brain (AI)
 */

// ============================================================================
// UTILITIES
// ============================================================================

function parseCurrency(val) {
    if (!val) return 0;
    return parseFloat(String(val).replace(/[^0-9.-]/g, '')) || 0;
}

function formatCurrency(val) {
    if (!val && val !== 0) return '-';
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(val);
}

function formatCompact(val) {
    if (!val && val !== 0) return '-';
    if (val >= 1000000) return '£' + (val / 1000000).toFixed(1) + 'M';
    if (val >= 1000) return '£' + (val / 1000).toFixed(0) + 'K';
    return '£' + val;
}

function formatPercent(val, decimals = 1) {
    if (!val && val !== 0) return '0%';
    return Number(val).toFixed(decimals) + '%';
}

// ============================================================================
// STATE
// ============================================================================

let sessionId = null;
let chatMessages = [];
let isLoading = false;
let activeRefiners = new Set();
let currentLenderCount = 0;

// ============================================================================
// TRANSACTION TYPE TOGGLE
// ============================================================================

function setupTransactionToggle() {
    const btnPurchase = document.getElementById('btn-purchase');
    const btnRefinance = document.getElementById('btn-refinance');
    const sectionPurchase = document.getElementById('section-purchase');
    const sectionRefinance = document.getElementById('section-refinance');
    
    btnPurchase.addEventListener('click', () => {
        btnPurchase.classList.add('active');
        btnRefinance.classList.remove('active');
        sectionPurchase.style.display = 'block';
        sectionRefinance.style.display = 'none';
        updateMetrics();
        updateLiveLenderCount();
    });
    
    btnRefinance.addEventListener('click', () => {
        btnRefinance.classList.add('active');
        btnPurchase.classList.remove('active');
        sectionRefinance.style.display = 'block';
        sectionPurchase.style.display = 'none';
        updateMetrics();
        updateLiveLenderCount();
    });
}

function getTransactionType() {
    return document.getElementById('btn-purchase').classList.contains('active') ? 'purchase' : 'refinance';
}

// ============================================================================
// INPUT MODE TOGGLE (Loan vs Deposit)
// ============================================================================

function setupInputModeToggle() {
    const btnLoan = document.getElementById('btn-mode-loan');
    const btnDeposit = document.getElementById('btn-mode-deposit');
    const sectionLoan = document.getElementById('section-loan-mode');
    const sectionDeposit = document.getElementById('section-deposit-mode');
    
    btnLoan.addEventListener('click', () => {
        btnLoan.classList.add('active');
        btnDeposit.classList.remove('active');
        sectionLoan.style.display = 'block';
        sectionDeposit.style.display = 'none';
        updateMetrics();
        updateLiveLenderCount();
    });
    
    btnDeposit.addEventListener('click', () => {
        btnDeposit.classList.add('active');
        btnLoan.classList.remove('active');
        sectionDeposit.style.display = 'block';
        sectionLoan.style.display = 'none';
        updateMetrics();
        updateLiveLenderCount();
    });
}

function getInputMode() {
    return document.getElementById('btn-mode-loan').classList.contains('active') ? 'loan' : 'deposit';
}

// ============================================================================
// VALUE GETTERS
// ============================================================================

function getLoanAmount() {
    const txnType = getTransactionType();
    const inputMode = getInputMode();
    
    if (txnType === 'refinance') {
        return parseCurrency(document.getElementById('input-loan-refi').value);
    }
    
    if (inputMode === 'deposit') {
        const deposit = parseCurrency(document.getElementById('input-deposit').value);
        const purchase = parseCurrency(document.getElementById('input-purchase-dep').value);
        return purchase > 0 ? purchase - deposit : 0;
    }
    
    return parseCurrency(document.getElementById('input-loan').value);
}

function getPurchasePrice() {
    const txnType = getTransactionType();
    const inputMode = getInputMode();
    
    if (txnType === 'refinance') return 0;
    
    if (inputMode === 'deposit') {
        return parseCurrency(document.getElementById('input-purchase-dep').value);
    }
    
    return parseCurrency(document.getElementById('input-purchase').value);
}

function getMarketValue() {
    const txnType = getTransactionType();
    
    if (txnType === 'refinance') {
        return parseCurrency(document.getElementById('input-value-refi').value);
    }
    
    // For purchase: use market value if provided, otherwise use purchase price
    const explicitValue = parseCurrency(document.getElementById('input-value').value);
    if (explicitValue > 0) return explicitValue;
    
    return getPurchasePrice();
}

// ============================================================================
// METRICS UPDATE
// ============================================================================

function updateMetrics() {
    const loan = getLoanAmount();
    const value = getMarketValue();
    const works = parseCurrency(document.getElementById('input-works').value);
    const gdv = parseCurrency(document.getElementById('input-gdv').value);
    const isRefurb = document.getElementById('toggle-refurb').checked;
    const inputMode = getInputMode();
    
    // Update loan display
    document.getElementById('metric-loan').textContent = loan > 0 ? formatCompact(loan) : '-';
    
    // Update value display
    document.getElementById('metric-value').textContent = value > 0 ? formatCompact(value) : '-';
    
    // Update deposit calc display
    if (inputMode === 'deposit') {
        document.getElementById('calc-loan-from-deposit').textContent = loan > 0 ? formatCurrency(loan) : '-';
    }
    
    // LTV
    const ltvEl = document.getElementById('metric-ltv');
    if (value > 0 && loan > 0) {
        const ltv = (loan / value) * 100;
        ltvEl.textContent = formatPercent(ltv);
        ltvEl.className = 'metric-value ' + (ltv <= 65 ? 'ltv-green' : ltv <= 75 ? 'ltv-amber' : 'ltv-red');
    } else {
        ltvEl.textContent = '0%';
        ltvEl.className = 'metric-value ltv-green';
    }
    
    // Refurb calculations
    updateRefurbCalcs(loan, value, works, gdv, isRefurb);
    
    // LTGDV in metrics bar
    const ltgdvContainer = document.getElementById('metric-ltgdv-container');
    if (isRefurb && gdv > 0 && loan > 0) {
        const totalFacility = loan + works;
        const ltgdv = (totalFacility / gdv) * 100;
        document.getElementById('metric-ltgdv').textContent = formatPercent(ltgdv);
        ltgdvContainer.style.display = 'block';
    } else {
        ltgdvContainer.style.display = 'none';
    }
}

function updateRefurbCalcs(loan, value, works, gdv, isRefurb) {
    const calcsPanel = document.getElementById('refurb-calcs');
    
    if (!isRefurb || works <= 0 || value <= 0) {
        calcsPanel.style.display = 'none';
        return;
    }
    
    calcsPanel.style.display = 'grid';
    
    // Works ratio
    const worksRatio = (works / value) * 100;
    document.getElementById('calc-works-ratio').textContent = formatPercent(worksRatio, 0);
    
    // Intensity badge
    const badge = document.getElementById('calc-intensity');
    let intensity, badgeClass;
    if (worksRatio < 30) {
        intensity = 'Light'; badgeClass = 'intensity-light';
    } else if (worksRatio < 50) {
        intensity = 'Medium'; badgeClass = 'intensity-medium';
    } else if (worksRatio < 100) {
        intensity = 'Heavy'; badgeClass = 'intensity-heavy';
    } else {
        intensity = 'Dev'; badgeClass = 'intensity-dev';
    }
    badge.textContent = intensity;
    badge.className = 'intensity-badge ' + badgeClass;
    
    // LTGDV
    const ltgdvEl = document.getElementById('calc-ltgdv');
    if (gdv > 0 && loan > 0) {
        const totalFacility = loan + works;
        const ltgdv = (totalFacility / gdv) * 100;
        ltgdvEl.textContent = formatPercent(ltgdv);
    } else {
        ltgdvEl.textContent = '-';
    }
}

// ============================================================================
// CONDITIONAL SECTIONS
// ============================================================================

function setupConditionals() {
    // Refurb toggle
    document.getElementById('toggle-refurb').addEventListener('change', (e) => {
        const section = document.getElementById('section-refurb');
        if (e.target.checked) {
            section.classList.add('visible');
        } else {
            section.classList.remove('visible');
        }
        updateMetrics();
        updateLiveLenderCount();
    });
}

// ============================================================================
// DEAL ESSENTIALS (for API)
// ============================================================================

function getDealEssentials() {
    const loan = getLoanAmount();
    const marketValue = getMarketValue();
    const purchasePrice = getPurchasePrice();
    const works = parseCurrency(document.getElementById('input-works').value);
    const gdv = parseCurrency(document.getElementById('input-gdv').value);
    const txnType = getTransactionType();
    const inputMode = getInputMode();
    const deposit = inputMode === 'deposit' ? parseCurrency(document.getElementById('input-deposit').value) : null;
    
    if (!loan || !marketValue) return null;
    
    // Calculate works intensity
    let worksIntensity = null;
    if (document.getElementById('toggle-refurb').checked && works > 0 && marketValue > 0) {
        const ratio = (works / marketValue) * 100;
        if (ratio < 30) worksIntensity = 'light';
        else if (ratio < 50) worksIntensity = 'medium';
        else if (ratio < 100) worksIntensity = 'heavy';
        else worksIntensity = 'very_heavy';
    }
    
    return {
        loan_amount: loan,
        purchase_price: purchasePrice,
        market_value: marketValue,
        transaction_type: txnType,
        input_mode: inputMode,
        deposit_available: deposit,
        property_type: document.getElementById('select-property').value,
        geography: document.getElementById('select-geography').value,
        charge_position: document.getElementById('select-charge').value,
        is_regulated: document.getElementById('toggle-regulated').checked,
        is_refurb: document.getElementById('toggle-refurb').checked,
        cost_of_works: works || null,
        gdv: gdv || null,
        works_intensity: worksIntensity,
        entity_type: document.getElementById('select-entity').value,
        active_refiners: Array.from(activeRefiners)
    };
}

// ============================================================================
// LIVE LENDER COUNT & AUTO-PROMPT
// ============================================================================

let lenderCountDebounce = null;

async function updateLiveLenderCount() {
    const essentials = getDealEssentials();
    const badge = document.getElementById('lender-count-badge');
    const countEl = document.getElementById('live-lender-count');
    const welcomeState = document.getElementById('welcome-state');
    const autoPromptState = document.getElementById('auto-prompt-state');
    
    if (!essentials) {
        countEl.textContent = '-';
        badge.className = 'lender-count-badge';
        welcomeState.style.display = 'flex';
        autoPromptState.style.display = 'none';
        return;
    }
    
    // Debounce
    if (lenderCountDebounce) clearTimeout(lenderCountDebounce);
    
    lenderCountDebounce = setTimeout(async () => {
        try {
            const response = await fetch('/api/filter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(essentials)
            });
            
            const data = await response.json();
            const count = data.summary?.eligible || data.eligible?.length || 0;
            currentLenderCount = count;
            
            countEl.textContent = count;
            
            // Update badge color
            if (count === 0) {
                badge.className = 'lender-count-badge none';
            } else if (count <= 5) {
                badge.className = 'lender-count-badge few';
            } else {
                badge.className = 'lender-count-badge';
            }
            
            // Show leverage hints if available
            displayLeverageHints(data.leverage_hints);
            
            // Show security hints if available
            displaySecurityHints(data.security_hints);
            
            // Show auto-prompt if we have matches and no chat yet
            if (count > 0 && chatMessages.length === 0) {
                welcomeState.style.display = 'none';
                autoPromptState.style.display = 'flex';
                document.getElementById('auto-prompt-count').textContent = count;
                updateRefinerChips(essentials);
            } else if (chatMessages.length === 0) {
                welcomeState.style.display = 'flex';
                autoPromptState.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Failed to get lender count:', error);
        }
    }, 300);
}

// ============================================================================
// LEVERAGE HINTS
// ============================================================================

function displayLeverageHints(hints) {
    // Remove any existing hints display
    const existingHints = document.getElementById('leverage-hints');
    if (existingHints) existingHints.remove();
    
    if (!hints || (!hints.refurb_unlocks?.length && !hints.serviced_interest_helps?.length)) {
        return;
    }
    
    // Create hints panel
    const hintsHtml = `
        <div id="leverage-hints" class="leverage-hints">
            <div class="hints-header">💡 Leverage opportunities</div>
            ${hints.refurb_unlocks?.length ? `
                <div class="hint-section">
                    <span class="hint-label">🔨 Add light refurb to unlock:</span>
                    <span class="hint-lenders">${hints.refurb_unlocks.slice(0, 3).map(h => 
                        `<span class="hint-lender">${h.name} (${h.refurb_ltv})</span>`
                    ).join(', ')}</span>
                </div>
            ` : ''}
            ${hints.serviced_interest_helps?.length ? `
                <div class="hint-section">
                    <span class="hint-label">💰 With serviced interest:</span>
                    <span class="hint-lenders">${hints.serviced_interest_helps.slice(0, 3).map(h => 
                        `<span class="hint-lender">${h.name}</span>`
                    ).join(', ')}</span>
                </div>
            ` : ''}
        </div>
    `;
    
    // Insert after the auto-prompt header
    const autoPromptHeader = document.querySelector('.auto-prompt-header');
    if (autoPromptHeader) {
        autoPromptHeader.insertAdjacentHTML('afterend', hintsHtml);
    }
}

function displaySecurityHints(hints) {
    // Remove any existing security hints
    const existingHints = document.getElementById('security-hints');
    if (existingHints) existingHints.remove();
    
    if (!hints || !hints.additional_security_helps || !hints.message) {
        return;
    }
    
    // Create security hints panel
    const hintsHtml = `
        <div id="security-hints" class="security-hints">
            <div class="hint-section">
                <span class="hint-label">🏠 Additional security:</span>
                <span class="hint-text">${hints.message}</span>
            </div>
        </div>
    `;
    
    // Insert after leverage hints if present, otherwise after auto-prompt header
    const leverageHints = document.getElementById('leverage-hints');
    if (leverageHints) {
        leverageHints.insertAdjacentHTML('afterend', hintsHtml);
    } else {
        const autoPromptHeader = document.querySelector('.auto-prompt-header');
        if (autoPromptHeader) {
            autoPromptHeader.insertAdjacentHTML('afterend', hintsHtml);
        }
    }
}

// ============================================================================
// DYNAMIC REFINER CHIPS
// ============================================================================

async function updateRefinerChips(essentials) {
    try {
        const response = await fetch('/api/refiner-options', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(essentials)
        });
        
        const data = await response.json();
        
        // Populate borrower refiners
        const borrowerChips = document.getElementById('refiner-chips-borrower');
        borrowerChips.innerHTML = (data.borrower_refiners || []).map(r => 
            renderRefinerChip(r)
        ).join('');
        
        // Populate deal refiners
        const dealChips = document.getElementById('refiner-chips-deal');
        dealChips.innerHTML = (data.deal_refiners || []).map(r => 
            renderRefinerChip(r)
        ).join('');
        
        // Populate product refiners
        const productChips = document.getElementById('refiner-chips-product');
        productChips.innerHTML = (data.product_refiners || []).map(r => 
            renderRefinerChip(r)
        ).join('');
        
        // Add click handlers
        document.querySelectorAll('.refiner-chip').forEach(chip => {
            chip.addEventListener('click', () => toggleRefinerChip(chip));
        });
        
    } catch (error) {
        console.error('Failed to get refiner options:', error);
        // Show default refiners on error
        showDefaultRefiners();
    }
}

function renderRefinerChip(refiner) {
    const isActive = activeRefiners.has(refiner.key);
    return `
        <div class="refiner-chip ${isActive ? 'active' : ''}" data-refiner="${refiner.key}">
            <span class="chip-icon">${refiner.icon}</span>
            <span class="chip-label">${refiner.label}</span>
            <span class="chip-count">${refiner.remaining}</span>
        </div>
    `;
}

function showDefaultRefiners() {
    const defaultBorrower = [
        { key: 'foreign_national', icon: '🌍', label: 'Foreign National', remaining: '?' },
        { key: 'expat', icon: '🛫', label: 'Expat', remaining: '?' },
        { key: 'adverse_credit', icon: '⚠️', label: 'Adverse Credit', remaining: '?' },
        { key: 'ftb', icon: '🏠', label: 'First Time Buyer', remaining: '?' }
    ];
    
    const defaultDeal = [
        { key: 'auction', icon: '🔨', label: 'Auction', remaining: '?' },
        { key: 'hmo', icon: '🏘️', label: 'HMO', remaining: '?' },
        { key: 'probate', icon: '📜', label: 'Probate', remaining: '?' }
    ];
    
    const defaultProduct = [
        { key: 'speed', icon: '⚡', label: 'Speed Critical', remaining: '?' },
        { key: 'serviced_interest', icon: '💰', label: 'Serviced Interest', remaining: '?' },
        { key: 'staged_funding', icon: '💸', label: 'Staged Funding', remaining: '?' }
    ];
    
    document.getElementById('refiner-chips-borrower').innerHTML = defaultBorrower.map(r => renderRefinerChip(r)).join('');
    document.getElementById('refiner-chips-deal').innerHTML = defaultDeal.map(r => renderRefinerChip(r)).join('');
    document.getElementById('refiner-chips-product').innerHTML = defaultProduct.map(r => renderRefinerChip(r)).join('');
    
    document.querySelectorAll('.refiner-chip').forEach(chip => {
        chip.addEventListener('click', () => toggleRefinerChip(chip));
    });
}

function toggleRefinerChip(chip) {
    const key = chip.dataset.refiner;
    if (activeRefiners.has(key)) {
        activeRefiners.delete(key);
        chip.classList.remove('active');
    } else {
        activeRefiners.add(key);
        chip.classList.add('active');
    }
}

// ============================================================================
// NEXT BUTTON - TRIGGER AI
// ============================================================================

async function handleNextButton() {
    const essentials = getDealEssentials();
    if (!essentials) {
        alert('Please fill in at least Loan Amount and Property Value');
        return;
    }
    
    // Build message based on active refiners
    let message = "Show me the best 3 lender options for this deal";
    
    const refinerDescriptions = {
        'foreign_national': 'borrower is a foreign national',
        'expat': 'borrower is an expat',
        'adverse_credit': 'borrower has adverse credit',
        'bankruptcy': 'borrower has bankruptcy/IVA history',
        'ftb': 'borrower is a first time buyer',
        'ftl': 'borrower is a first time landlord',
        'auction': 'this is an auction purchase',
        'hmo': 'this is an HMO conversion',
        'probate': 'property is in probate',
        'speed': 'speed is critical',
        'serviced_interest': 'can service interest monthly',
        'staged_funding': 'need staged/arrears funding for works',
        'dual_legal': 'prefer dual legal rep'
    };
    
    if (activeRefiners.size > 0) {
        const factors = Array.from(activeRefiners)
            .map(key => refinerDescriptions[key] || key)
            .join(', ');
        message = `Show me the best 3 lender options. Key factors: ${factors}`;
    }
    
    // Hide auto-prompt
    document.getElementById('auto-prompt-state').style.display = 'none';
    
    // Send to AI
    await sendMessageDirect(message);
}

// ============================================================================
// CHAT FUNCTIONS
// ============================================================================

async function startNewChat() {
    try {
        const response = await fetch('/api/chat/new', { method: 'POST' });
        const data = await response.json();
        sessionId = data.session_id;
        chatMessages = [];
        return sessionId;
    } catch (error) {
        console.error('Failed to start chat:', error);
        sessionId = 'local-' + Date.now();
        return sessionId;
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || isLoading) return;
    
    input.value = '';
    await sendMessageDirect(message);
}

async function sendMessageDirect(message) {
    const essentials = getDealEssentials();
    if (!essentials) {
        addMessage('system', 'Please fill in loan amount and property value first.');
        return;
    }
    
    // Start session if needed
    if (!sessionId) {
        await startNewChat();
    }
    
    // Hide welcome/auto-prompt
    document.getElementById('welcome-state').style.display = 'none';
    document.getElementById('auto-prompt-state').style.display = 'none';
    
    // Add user message
    addMessage('user', message);
    chatMessages.push({ role: 'user', content: message });
    
    // Show loading
    isLoading = true;
    document.getElementById('btn-send').disabled = true;
    addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                message: message,
                deal_essentials: essentials
            })
        });
        
        const data = await response.json();
        removeTypingIndicator();
        
        if (data.response) {
            addMessage('assistant', data.response);
            chatMessages.push({ role: 'assistant', content: data.response });
        } else {
            addMessage('system', 'No response received. Please try again.');
        }
        
    } catch (error) {
        removeTypingIndicator();
        addMessage('system', `Error: ${error.message}`);
    } finally {
        isLoading = false;
        document.getElementById('btn-send').disabled = false;
    }
}

function addMessage(role, content) {
    const container = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : role === 'assistant' ? '🧠' : 'ℹ️';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessageContent(content);
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function formatMessageContent(content) {
    // Convert markdown-like formatting to HTML
    let html = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n- /g, '</p><ul><li>')
        .replace(/\n/g, '<br>');
    
    // Wrap in paragraph
    html = '<p>' + html + '</p>';
    
    // Fix list formatting
    html = html.replace(/<\/p><ul>/g, '</p><ul>');
    html = html.replace(/<li>(.*?)<br>/g, '<li>$1</li>');
    
    // Add contact buttons for lender names mentioned
    // Look for patterns like "1. **Lender Name**" or "**Lender Name:**"
    html = html.replace(/<strong>([A-Za-z][A-Za-z0-9\s&\-']+(?:Capital|Finance|Bank|Trust|Lending|Bridge|Bridging|Mortgages|Property|Ltd|Group|Holdings)?)<\/strong>/g, 
        (match, lenderName) => {
            // Clean up lender name
            const cleanName = lenderName.trim().replace(/:$/, '');
            // Only add button if it looks like a lender name (has capital letter, multiple words, or common suffixes)
            if (cleanName.length > 3 && (cleanName.includes(' ') || /Capital|Finance|Bank|Trust|Lending|Bridge|Mortgages|Property|Ltd|Group/i.test(cleanName))) {
                return `<strong>${cleanName}</strong> <button class="contact-lender-btn" onclick="openContactModal('${cleanName.replace(/'/g, "\\'")}')">📞 Contact</button>`;
            }
            return match;
        }
    );
    
    return html;
}

function addTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const indicator = document.createElement('div');
    indicator.className = 'message assistant';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="message-avatar">🧠</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// ============================================================================
// QUICK PROMPTS
// ============================================================================

function setupQuickPrompts() {
    document.querySelectorAll('.quick-prompt').forEach(prompt => {
        prompt.addEventListener('click', () => {
            const text = prompt.dataset.prompt;
            document.getElementById('chat-input').value = text;
            sendMessage();
        });
    });
}

// ============================================================================
// CLEAR FORM
// ============================================================================

function clearForm() {
    if (!confirm('Clear all form data and start over?')) return;
    
    // Reset inputs
    document.querySelectorAll('input[type="text"], input[type="number"]').forEach(el => el.value = '');
    document.querySelectorAll('select').forEach(el => el.selectedIndex = 0);
    document.querySelectorAll('input[type="checkbox"]').forEach(el => el.checked = false);
    
    // Reset toggles to defaults
    document.getElementById('btn-purchase').classList.add('active');
    document.getElementById('btn-refinance').classList.remove('active');
    document.getElementById('section-purchase').style.display = 'block';
    document.getElementById('section-refinance').style.display = 'none';
    
    document.getElementById('btn-mode-loan').classList.add('active');
    document.getElementById('btn-mode-deposit').classList.remove('active');
    document.getElementById('section-loan-mode').style.display = 'block';
    document.getElementById('section-deposit-mode').style.display = 'none';
    
    // Hide conditionals
    document.querySelectorAll('.conditional').forEach(el => el.classList.remove('visible'));
    
    // Reset state
    activeRefiners.clear();
    chatMessages = [];
    sessionId = null;
    
    // Clear chat messages display
    const chatContainer = document.getElementById('chat-messages');
    chatContainer.innerHTML = `
        <div class="welcome-state" id="welcome-state">
            <div class="icon">👈</div>
            <h3>Start with the basics</h3>
            <p>Fill in loan amount and property value to see matching lenders</p>
        </div>
        <div class="auto-prompt-state" id="auto-prompt-state">
            <div class="auto-prompt-header">
                <h3><span id="auto-prompt-count">0</span> lenders match your criteria</h3>
                <p>Narrow down further or click NEXT for AI recommendations</p>
            </div>
            <div class="refiner-section" id="refiner-section-borrower">
                <div class="refiner-section-title">Borrower Factors</div>
                <div class="refiner-chips" id="refiner-chips-borrower"></div>
            </div>
            <div class="refiner-section" id="refiner-section-deal">
                <div class="refiner-section-title">Deal Factors</div>
                <div class="refiner-chips" id="refiner-chips-deal"></div>
            </div>
            <div class="refiner-section" id="refiner-section-product">
                <div class="refiner-section-title">Product Preferences</div>
                <div class="refiner-chips" id="refiner-chips-product"></div>
            </div>
            <div class="next-button-container">
                <button class="btn-next" id="btn-next">NEXT → Get AI Recommendations</button>
            </div>
        </div>
    `;
    
    // Re-attach NEXT button handler
    document.getElementById('btn-next').addEventListener('click', handleNextButton);
    
    // Update metrics
    updateMetrics();
    updateLiveLenderCount();
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Setup toggles
    setupTransactionToggle();
    setupInputModeToggle();
    setupConditionals();
    setupQuickPrompts();
    
    // Currency inputs - live update
    const currencyInputs = [
        'input-loan', 'input-purchase', 'input-value',
        'input-loan-refi', 'input-value-refi',
        'input-deposit', 'input-purchase-dep',
        'input-works', 'input-gdv'
    ];
    
    currencyInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => {
                updateMetrics();
                updateLiveLenderCount();
            });
        }
    });
    
    // Select changes
    ['select-property', 'select-geography', 'select-charge', 'select-entity'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                updateLiveLenderCount();
            });
        }
    });
    
    // Toggle changes
    document.getElementById('toggle-regulated').addEventListener('change', updateLiveLenderCount);
    
    // Buttons
    document.getElementById('btn-clear').addEventListener('click', clearForm);
    document.getElementById('btn-next').addEventListener('click', handleNextButton);
    document.getElementById('btn-send').addEventListener('click', sendMessage);
    
    // Enter key in chat input
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Initial state
    updateMetrics();
    
    console.log('Bridging Brain v4 initialized');
});

// ============================================================================
// CONTACT LENDER MODAL
// ============================================================================

let currentContactLender = null;

function openContactModal(lenderName) {
    currentContactLender = lenderName;
    const modal = document.getElementById('contact-modal');
    const title = document.getElementById('contact-modal-title');
    
    title.textContent = `Contact ${lenderName}`;
    
    // Fetch contact details
    fetch(`/api/lender/${encodeURIComponent(lenderName)}/contact`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('contact-bdm-name').textContent = data.contact?.bdm_name || 'New Business Team';
            document.getElementById('contact-email').textContent = data.contact?.email || 'Email not available';
            document.getElementById('contact-phone').textContent = data.contact?.phone || 'Phone not available';
            
            // Show refurb section if deal is refurb
            const essentials = getDealEssentials();
            const refurbSection = document.getElementById('aip-refurb-section');
            if (essentials && essentials.is_refurb) {
                refurbSection.style.display = 'block';
            } else {
                refurbSection.style.display = 'none';
            }
            
            // Reset to step 1
            showContactStep1();
            modal.style.display = 'flex';
        })
        .catch(err => {
            console.error('Failed to fetch contact details:', err);
            alert('Failed to load contact details');
        });
}

function closeContactModal() {
    document.getElementById('contact-modal').style.display = 'none';
    currentContactLender = null;
}

function showContactStep1() {
    document.getElementById('contact-step-1').style.display = 'block';
    document.getElementById('contact-step-2').style.display = 'none';
    document.getElementById('contact-step-3').style.display = 'none';
}

function contactOwnWay() {
    // Just close the modal - they have the contact details
    closeContactModal();
}

function showAIPForm() {
    document.getElementById('contact-step-1').style.display = 'none';
    document.getElementById('contact-step-2').style.display = 'block';
    document.getElementById('contact-step-3').style.display = 'none';
}

function getAIPDetails() {
    return {
        borrower_name: document.getElementById('aip-borrower-name').value || null,
        borrower_type: document.getElementById('aip-borrower-type').value || null,
        is_homeowner: document.getElementById('aip-homeowner').value === 'yes' ? true : 
                      document.getElementById('aip-homeowner').value === 'no' ? false : null,
        assets_liabilities: document.getElementById('aip-al-position').value || null,
        property_address: document.getElementById('aip-property-address').value || null,
        additional_security_address: document.getElementById('aip-additional-security').value || null,
        refurb_experience: document.getElementById('aip-experience').value || null,
        gdv_estimate: document.getElementById('aip-gdv').value || null,
        works_schedule: document.getElementById('aip-works-schedule').value || null,
        exit_strategy: document.getElementById('aip-exit-strategy').value || null,
        exit_timeframe: document.getElementById('aip-timeframe').value || null,
        urgency: document.getElementById('aip-urgency').value || null,
        additional_notes: document.getElementById('aip-notes').value || null
    };
}

async function generateDealPresentation() {
    const essentials = getDealEssentials();
    const aipDetails = getAIPDetails();
    
    try {
        const response = await fetch('/api/contact-lender', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lender_name: currentContactLender,
                deal_essentials: essentials,
                aip_details: aipDetails,
                generate_email: true
            })
        });
        
        const data = await response.json();
        
        // Show validation result
        const validationDiv = document.getElementById('validation-result');
        if (data.still_fits) {
            validationDiv.innerHTML = `
                <div class="validation-success">
                    ✅ <strong>Confirmed:</strong> Based on the details provided, this deal appears to fit ${currentContactLender}'s criteria.
                </div>
            `;
        } else {
            let warningsHtml = data.warnings.map(w => `<li>${w}</li>`).join('');
            let alternativesHtml = '';
            if (data.alternative_suggestions && data.alternative_suggestions.length > 0) {
                alternativesHtml = `
                    <div class="alternatives">
                        <strong>You might also consider:</strong>
                        <ul>
                            ${data.alternative_suggestions.map(a => `<li><strong>${a.name}</strong> - ${a.reason}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
            validationDiv.innerHTML = `
                <div class="validation-warning">
                    <div class="warning-title">⚠️ Heads up - some details may affect this lender's appetite:</div>
                    <ul class="warning-list">${warningsHtml}</ul>
                    ${alternativesHtml}
                </div>
            `;
        }
        
        // Show email template
        document.getElementById('email-template').textContent = data.email_template;
        
        // Show step 3
        document.getElementById('contact-step-1').style.display = 'none';
        document.getElementById('contact-step-2').style.display = 'none';
        document.getElementById('contact-step-3').style.display = 'block';
        
    } catch (err) {
        console.error('Failed to generate deal presentation:', err);
        alert('Failed to generate deal presentation. Please try again.');
    }
}

function copyEmailTemplate() {
    const template = document.getElementById('email-template').textContent;
    navigator.clipboard.writeText(template).then(() => {
        const btn = document.querySelector('.btn-copy');
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = '📋 Copy to Clipboard';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('contact-modal');
    if (e.target === modal) {
        closeContactModal();
    }
});
