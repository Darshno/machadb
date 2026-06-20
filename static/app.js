document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('query-input');
    const runBtn = document.getElementById('run-btn');
    const resultsContent = document.getElementById('results-content');
    const statusIndicator = document.getElementById('status-indicator');

    // Run on Ctrl+Enter
    queryInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            executeQuery();
        }
    });

    runBtn.addEventListener('click', executeQuery);

    async function executeQuery() {
        const query = queryInput.value.trim();
        if (!query) return;

        // UI Loading state
        runBtn.disabled = true;
        runBtn.innerHTML = `
            <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 1s linear infinite;"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="4.93" x2="19.07" y2="7.76"></line></svg>
            Running...
        `;
        resultsContent.innerHTML = `<div class="empty-state">Executing macha...</div>`;
        statusIndicator.className = 'status-badge hidden';

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const data = await res.json();
            
            if (data.success) {
                showSuccess(data.data);
            } else {
                showError(data.error);
            }
        } catch (err) {
            showError("Network error macha! Backend is down.");
        } finally {
            // Restore button
            runBtn.disabled = false;
            runBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                Run Query
            `;
        }
    }

    function showSuccess(data) {
        statusIndicator.textContent = '✔ Success';
        statusIndicator.className = 'status-badge status-success';

        if (Array.isArray(data)) {
            renderTable(data);
        } else if (typeof data === 'string') {
            resultsContent.innerHTML = `<div class="string-output">${escapeHtml(data)}</div>`;
        } else {
            resultsContent.innerHTML = `<div class="string-output">${JSON.stringify(data, null, 2)}</div>`;
        }
    }

    function showError(msg) {
        statusIndicator.textContent = '❌ Error';
        statusIndicator.className = 'status-badge status-error';
        resultsContent.innerHTML = `<div class="error-output">${escapeHtml(msg)}</div>`;
    }

    function renderTable(rows) {
        if (rows.length === 0) {
            resultsContent.innerHTML = `<div class="string-output">Khali ide macha. (0 rows)</div>`;
            return;
        }

        const columns = Object.keys(rows[0]);
        let html = `<table><thead><tr>`;
        
        columns.forEach(col => {
            html += `<th>${escapeHtml(col)}</th>`;
        });
        html += `</tr></thead><tbody>`;

        rows.forEach(row => {
            html += `<tr>`;
            columns.forEach(col => {
                let val = row[col];
                if (val === null) val = "null";
                html += `<td>${escapeHtml(String(val))}</td>`;
            });
            html += `</tr>`;
        });

        html += `</tbody></table>`;
        html += `<div style="margin-top: 1rem; color: var(--text-muted); font-size: 0.85rem;">(${rows.length} rows)</div>`;
        
        resultsContent.innerHTML = html;
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});

// Add keyframes for spinner dynamically
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin {
    100% { transform: rotate(360deg); }
}
`;
document.head.appendChild(style);
