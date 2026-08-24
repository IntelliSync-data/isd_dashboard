/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const LOADING_PHASES = [
    { at: 0,  text: _t("Connecting to AI system...") },
    { at: 5,  text: _t("AI is querying data from the system...") },
    { at: 12, text: _t("Collecting transaction and revenue data...") },
    { at: 20, text: _t("AI is analyzing and aggregating data...") },
    { at: 35, text: _t("Generating charts and visual reports...") },
    { at: 50, text: _t("Finalizing report, please wait...") },
    { at: 70, text: _t("Report almost done, verifying data...") },
    { at: 90, text: _t("Almost finished, just a few more seconds...") },
];

const REPORT_TYPES = [
    { value: "revenue", label: _t("Revenue Report") },
    { value: "comparison", label: _t("Revenue Comparison") },
];

const PERIOD_TYPES = [
    { value: "week", label: _t("Week") },
    { value: "month", label: _t("Month") },
    { value: "quarter", label: _t("Quarter") },
    { value: "year", label: _t("Year") },
];

export class IsdAiDashboard extends Component {
    static template = "isd_dashboard.AiDashboard";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            reportType: "revenue",
            periodType: "month",
            periodValue: "",
            comparePeriodValue: "",
            periodOptions: [],

            loading: false,
            error: null,
            hasResult: false,
            elapsed: 0,
            loadingText: LOADING_PHASES[0].text,
            currentLabel: "",

            savedReports: [],
            showSaved: false,

            canRunPrompt: false,
        });

        this.reportTypes = REPORT_TYPES;
        this.periodTypes = PERIOD_TYPES;

        this._pollTimer = null;
        this._elapsedTimer = null;

        onWillStart(async () => {
            try {
                const result = await rpc("/isd_dashboard/check_permission", {});
                this.state.canRunPrompt = result.can_run_prompt || false;
            } catch {
                this.state.canRunPrompt = false;
            }
            await this._loadPeriodOptions();
            await this._loadSavedReports();
        });
    }

    async _loadPeriodOptions() {
        try {
            const options = await rpc("/isd_dashboard/period_options", {
                period_type: this.state.periodType,
            });
            this.state.periodOptions = options || [];
            this.state.periodValue = "";
            this.state.comparePeriodValue = "";
        } catch (err) {
            console.error("Failed to load period options:", err);
        }
    }

    async _loadSavedReports() {
        try {
            const reports = await rpc("/isd_dashboard/saved_reports", {});
            this.state.savedReports = reports || [];
        } catch (err) {
            console.error("Failed to load saved reports:", err);
        }
    }

    onReportTypeChange(ev) {
        this.state.reportType = ev.target.value;
    }

    async onPeriodTypeChange(ev) {
        this.state.periodType = ev.target.value;
        await this._loadPeriodOptions();
    }

    onPeriodChange(ev) {
        this.state.periodValue = ev.target.value;
    }

    onComparePeriodChange(ev) {
        this.state.comparePeriodValue = ev.target.value;
    }

    _updateLoadingText() {
        const elapsed = this.state.elapsed;
        let text = LOADING_PHASES[0].text;
        for (const phase of LOADING_PHASES) {
            if (elapsed >= phase.at) text = phase.text;
        }
        this.state.loadingText = text;
    }

    async onSubmit() {
        if (this.state.loading || !this.state.periodValue) return;
        await this._submitReport(false);
    }

    async onRefresh() {
        if (this.state.loading || !this.state.periodValue) return;
        await this._submitReport(true);
    }

    async _submitReport(forceRefresh) {
        this.state.loading = true;
        this.state.error = null;
        this.state.hasResult = false;
        this.state.elapsed = 0;
        this.state.showSaved = false;
        this.state.loadingText = LOADING_PHASES[0].text;
        this._clearOutput();

        this._elapsedTimer = setInterval(() => {
            this.state.elapsed += 1;
            this._updateLoadingText();
        }, 1000);

        try {
            const params = {
                report_type: this.state.reportType,
                period_type: this.state.periodType,
                period_value: this.state.periodValue,
                force_refresh: forceRefresh,
            };
            if (this.state.reportType === "comparison") {
                params.compare_period_value = this.state.comparePeriodValue;
            }

            const result = await rpc("/isd_dashboard/submit_report", params);

            if (result.error) {
                this._stopTimers();
                this.state.loading = false;
                this.state.error = result.error;
                return;
            }

            if (result.period_label) {
                this.state.currentLabel = result.period_label;
            }

            if (result.status === "done" && result.html) {
                this._stopTimers();
                this.state.loading = false;
                this.state.hasResult = true;
                if (result.from_cache) {
                    this.notification.add(_t("Already available — no AI tokens used."), { type: "success" });
                }
                setTimeout(() => this._injectHtml(result.html), 50);
                this._loadSavedReports();
                return;
            }

            if (result.task_id) {
                this._startPolling(result.task_id);
            }
        } catch (err) {
            this._stopTimers();
            this.state.loading = false;
            this.state.error = _t("Cannot connect to server.");
            console.error("ISD Dashboard error:", err);
        }
    }

    onToggleSaved() {
        this.state.showSaved = !this.state.showSaved;
    }

    async onViewSaved(ev) {
        const reportId = parseInt(ev.target.dataset.reportId);
        if (!reportId) return;
        try {
            const result = await rpc("/isd_dashboard/view_report", { report_id: reportId });
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.hasResult = true;
            this.state.showSaved = false;
            this.state.error = null;
            setTimeout(() => this._injectHtml(result.html), 50);
        } catch (err) {
            this.state.error = _t("Error loading report.");
        }
    }

    _startPolling(taskId) {
        this._pollTimer = setInterval(async () => {
            try {
                const result = await rpc("/isd_dashboard/poll", { task_id: taskId });
                if (result.status === "pending") return;

                this._stopTimers();
                this.state.loading = false;

                if (result.status === "error") {
                    this.state.error = result.error;
                } else if (result.status === "done") {
                    this.state.hasResult = true;
                    setTimeout(() => this._injectHtml(result.html), 50);
                    this._loadSavedReports();
                }
            } catch (err) {
                this._stopTimers();
                this.state.loading = false;
                this.state.error = _t("Connection error. Please try again.");
            }
        }, 3000);
    }

    _stopTimers() {
        if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
        if (this._elapsedTimer) { clearInterval(this._elapsedTimer); this._elapsedTimer = null; }
    }

    _clearOutput() {
        const container = document.getElementById("isd-html-output");
        if (container) container.innerHTML = "";
    }

    _injectHtml(html, retries = 0) {
        const container = document.getElementById("isd-html-output");
        if (!container) {
            if (retries < 10) setTimeout(() => this._injectHtml(html, retries + 1), 100);
            return;
        }
        container.innerHTML = "";
        const div = document.createElement("div");
        div.innerHTML = html;

        const scripts = div.querySelectorAll("script");
        const externalScripts = [];
        const inlineScripts = [];
        scripts.forEach((s) => {
            if (s.src) externalScripts.push(s.src);
            else inlineScripts.push(s.textContent);
            s.remove();
        });
        container.innerHTML = div.innerHTML;
        container.querySelectorAll("canvas").forEach((c) => {
            c.style.maxHeight = "";
            c.style.height = "";
        });

        const ensureChartJs = () => new Promise((resolve) => {
            if (window.Chart) { resolve(); return; }
            const cdnUrl = externalScripts.find((s) => s.includes("chart.js") || s.includes("chartjs"));
            if (!cdnUrl) { resolve(); return; }
            const existing = document.querySelector('script[src*="chart.js"], script[src*="chartjs"]');
            if (existing) {
                if (window.Chart) resolve();
                else { existing.addEventListener("load", resolve); setTimeout(resolve, 3000); }
                return;
            }
            const el = document.createElement("script");
            el.src = cdnUrl;
            el.onload = resolve;
            el.onerror = resolve;
            document.head.appendChild(el);
        });

        const runAll = async () => {
            await ensureChartJs();
            await new Promise((r) => setTimeout(r, 200));
            for (const code of inlineScripts) {
                try {
                    const scriptEl = document.createElement("script");
                    scriptEl.textContent = "(function(){" + code + "})();";
                    document.body.appendChild(scriptEl);
                    scriptEl.remove();
                } catch (e) {
                    console.warn("Chart script error:", e);
                }
            }
        };
        runAll();
    }

    onPrint() {
        const container = document.getElementById("isd-html-output");
        if (!container) return;
        const clone = container.cloneNode(true);
        const canvases = container.querySelectorAll("canvas");
        const cloneCanvases = clone.querySelectorAll("canvas");
        canvases.forEach((canvas, i) => {
            try {
                const img = document.createElement("img");
                img.src = canvas.toDataURL("image/png");
                img.style.width = "100%";
                cloneCanvases[i].parentNode.replaceChild(img, cloneCanvases[i]);
            } catch (e) { /* ignore */ }
        });
        const cssLinks = [];
        document.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
            if (link.href) cssLinks.push(link.href);
        });
        const cssHtml = cssLinks.map((href) => '<link rel="stylesheet" href="' + href + '"/>').join("\n");
        const printWindow = window.open("", "_blank");
        printWindow.document.write("<!DOCTYPE html><html><head><title>" + _t("Report") + "</title>" +
            cssHtml + "<style>body{padding:20px;font-size:13px;background:#fff!important;}img{max-width:100%;height:auto;}" +
            "@media print{body{padding:10px;}}</style></head><body>" + clone.innerHTML + "</body></html>");
        printWindow.document.close();
        printWindow.onload = () => printWindow.print();
    }

    onClear() {
        this._stopTimers();
        this.state.error = null;
        this.state.hasResult = false;
        this.state.loading = false;
        this.state.elapsed = 0;
        this._clearOutput();
    }
}

registry.category("actions").add("isd_ai_dashboard", IsdAiDashboard);
