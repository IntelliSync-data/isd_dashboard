/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const LOADING_PHASES = [
    { at: 0,  text: "\u0110ang k\u1EBFt n\u1ED1i t\u1EDBi h\u1EC7 th\u1ED1ng AI..." },
    { at: 5,  text: "AI \u0111ang truy v\u1EA5n d\u1EEF li\u1EC7u t\u1EEB h\u1EC7 th\u1ED1ng..." },
    { at: 12, text: "\u0110ang thu th\u1EADp d\u1EEF li\u1EC7u giao d\u1ECBch v\u00E0 doanh thu..." },
    { at: 20, text: "AI \u0111ang ph\u00E2n t\u00EDch v\u00E0 t\u1ED5ng h\u1EE3p d\u1EEF li\u1EC7u..." },
    { at: 35, text: "\u0110ang t\u1EA1o bi\u1EC3u \u0111\u1ED3 v\u00E0 b\u00E1o c\u00E1o tr\u1EF1c quan..." },
    { at: 50, text: "\u0110ang ho\u00E0n thi\u1EC7n b\u00E1o c\u00E1o, vui l\u00F2ng ch\u1EDD th\u00EAm..." },
    { at: 70, text: "B\u00E1o c\u00E1o g\u1EA7n ho\u00E0n th\u00E0nh, \u0111ang ki\u1EC3m tra l\u1EA1i d\u1EEF li\u1EC7u..." },
    { at: 90, text: "S\u1EAFp xong r\u1ED3i, ch\u1EC9 th\u00EAm v\u00E0i gi\u00E2y n\u1EEFa..." },
];

const REPORT_TYPES = [
    { value: "revenue", label: "B\u00E1o c\u00E1o doanh thu" },
    { value: "comparison", label: "So s\u00E1nh doanh thu" },
];

const PERIOD_TYPES = [
    { value: "week", label: "Tu\u1EA7n" },
    { value: "month", label: "Th\u00E1ng" },
    { value: "quarter", label: "Qu\u00FD" },
    { value: "year", label: "N\u0103m" },
];

export class IsdAiDashboard extends Component {
    static template = "isd_dashboard.AiDashboard";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            // Report config
            reportType: "revenue",
            periodType: "month",
            periodValue: "",
            comparePeriodValue: "",
            periodOptions: [],

            // Execution state
            loading: false,
            error: null,
            hasResult: false,
            elapsed: 0,
            loadingText: LOADING_PHASES[0].text,
            currentLabel: "",

            // Saved reports
            savedReports: [],
            showSaved: false,
        });

        this.reportTypes = REPORT_TYPES;
        this.periodTypes = PERIOD_TYPES;

        this._pollTimer = null;
        this._elapsedTimer = null;

        onWillStart(async () => {
            await this._loadPeriodOptions();
            await this._loadSavedReports();
        });
    }

    // ── Data loading ──

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

    // ── Event handlers ──

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

    // ── Submit report ──

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

            // Cached result
            if (result.status === "done" && result.html) {
                this._stopTimers();
                this.state.loading = false;
                this.state.hasResult = true;
                if (result.from_cache) {
                    this.notification.add("\u0110\u00E3 c\u00F3 s\u1EB5n - kh\u00F4ng t\u1ED1n token AI.", { type: "success" });
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
            this.state.error = "Kh\u00F4ng th\u1EC3 k\u1EBFt n\u1ED1i \u0111\u1EBFn server.";
            console.error("ISD Dashboard error:", err);
        }
    }

    // ── Saved reports ──

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
            this.state.error = "L\u1ED7i khi t\u1EA3i b\u00E1o c\u00E1o.";
        }
    }

    // ── Polling ──

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
                this.state.error = "L\u1ED7i k\u1EBFt n\u1ED1i. Vui l\u00F2ng th\u1EED l\u1EA1i.";
            }
        }, 3000);
    }

    // ── Utilities ──

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
        printWindow.document.write("<!DOCTYPE html><html><head><title>B\u00E1o c\u00E1o</title>" +
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
