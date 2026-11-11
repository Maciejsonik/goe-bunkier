// DevTools Console Collector for X.com (#bunkier Worlds 2026)
// Works cleanly with X's Trusted Types CSP (uses DOM APIs only, no innerHTML)
// and accumulates deduplicated tweets in localStorage across multiple search queries.

(() => {
    const STORAGE_KEY = "bunkier_x_collector_v1";
    const HUD_ID = "bunkier-x-collector-hud";

    function parseXCount(raw) {
        if (!raw) return 0;
        const txt = String(raw).trim();
        const match = txt.match(/(\d+(?:[., \u00a0\u202f]\d+)*)\s*(tys\.?|mln|mld|[kmbKMB])?/i);
        if (!match) return 0;
        const numPart = match[1].trim();
        const suffix = (match[2] || "").toLowerCase();

        if (suffix) {
            const val = parseFloat(numPart.replace(/[\s\u00a0\u202f]+/g, "").replace(",", "."));
            if (!Number.isFinite(val)) return 0;
            if (suffix.startsWith("tys") || suffix === "k") return Math.round(val * 1000);
            if (suffix === "mln" || suffix === "m") return Math.round(val * 1_000_000);
            if (suffix === "mld" || suffix === "b") return Math.round(val * 1_000_000_000);
            return Math.round(val);
        }

        const intDigits = numPart.replace(/[\s\u00a0\u202f.,]+/g, "");
        const parsed = parseInt(intDigits, 10);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function loadStore() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch (err) {
            console.warn("[Bunkier X] Błąd odczytu localStorage:", err);
            return {};
        }
    }

    function saveStore(mapObj) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(mapObj));
    }

    function snowflakeToIso(idStr) {
        try {
            const ms = Number((BigInt(idStr) >> 22n) + 1288834974657n);
            return new Date(ms).toISOString();
        } catch {
            return "";
        }
    }

    function isInNestedQuote(article, el, mainUser) {
        if (!mainUser) return false;
        let cur = el.parentElement;
        while (cur && cur !== article) {
            const nestedUser = cur.querySelector('[data-testid="User-Name"]');
            if (nestedUser && nestedUser !== mainUser) {
                return true;
            }
            cur = cur.parentElement;
        }
        return false;
    }

    function outerElements(article, selector, mainUser) {
        return Array.from(article.querySelectorAll(selector)).filter(
            (el) => !isInNestedQuote(article, el, mainUser)
        );
    }

    function readMetricInfo(article, selectors, mainUser) {
        for (const sel of selectors) {
            const el = outerElements(article, sel, mainUser)[0] || article.querySelector(sel);
            if (!el) continue;
            const rawText = (el.innerText || "").trim();
            const byText = parseXCount(rawText);
            if (byText > 0) return { count: byText, rawText };
            const byAria = parseXCount(el.getAttribute("aria-label"));
            if (byAria > 0) return { count: byAria, rawText };
        }
        return { count: 0, rawText: "" };
    }

    function extractBodyFromInnerText(rawInnerText, handle, metricTexts) {
        const lines = (rawInnerText || "").split("\n").map((s) => s.trim());
        const handleLower = ("@" + handle).toLowerCase();

        let handleIdx = lines.findIndex((l) => l.toLowerCase() === handleLower);
        if (handleIdx === -1) {
            handleIdx = lines.findIndex((l) => l.toLowerCase().includes(handleLower));
        }

        let authorName = handle;
        if (handleIdx > 0) {
            for (let i = handleIdx - 1; i >= 0; i -= 1) {
                const cand = lines[i];
                if (!cand || /podał|reposted|przypięt|pinned/i.test(cand)) continue;
                authorName = cand;
                break;
            }
        }

        let start = handleIdx >= 0 ? handleIdx + 1 : 0;
        let isReply = false;
        const dateLineRe =
            /^(?:\d+\s+(?:sty|lut|mar|kwi|maj|cze|lip|sie|wrz|paź|lis|gru)(?:\s+\d{4})?|\d+\s*(?:min|m|godz\.?|h|sek\.?|s|dni|d)|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+(?:,\s*\d{4})?|Teraz|Now)$/i;

        // Skip header separators, follow button, relative/short date, and reply preamble
        let inReplyHeader = false;
        while (start < lines.length) {
            const l = lines[start];
            if (
                !l ||
                l === "·" ||
                l === "•" ||
                /^(?:Obserwuj|Follow|Obserwowany|Following|Subskrybuj)$/i.test(l) ||
                dateLineRe.test(l)
            ) {
                start += 1;
                continue;
            }
            if (/^(?:W odpowiedzi do|Odpowiadanie|Replying to)/i.test(l)) {
                isReply = true;
                inReplyHeader = true;
                start += 1;
                continue;
            }
            if (inReplyHeader && (/^@[A-Za-z0-9_]+$/.test(l) || /^(?:i|and|oraz)$/i.test(l))) {
                start += 1;
                continue;
            }
            inReplyHeader = false;
            break;
        }

        // Stop before quoted tweet block (explicit "Cytat"/"Quote" or @otherHandle + date line)
        let end = lines.length;
        for (let i = start; i < lines.length; i += 1) {
            if (/^(?:Cytat|Quote)$/i.test(lines[i])) {
                const windowAhead = lines.slice(i + 1, i + 5).join("\n");
                if (/^@[A-Za-z0-9_]+/m.test(windowAhead)) {
                    end = i;
                    break;
                }
            }
            if (i > start && /^@[A-Za-z0-9_]+$/.test(lines[i]) && lines[i].toLowerCase() !== handleLower) {
                const nextTwo = lines.slice(i + 1, i + 3).filter((x) => x && x !== "·" && x !== "•");
                if (nextTwo.some((x) => dateLineRe.test(x))) {
                    end = Math.max(start, i - 1);
                    break;
                }
            }
        }

        // Strip trailing action-bar counters and footer chrome from bottom up
        const countOnlyRe = /^\d+(?:[., \u00a0\u202f]\d+)*\s*(?:tys\.?|mln|mld|[kmb])?$/i;
        const footerNoiseRe =
            /^(?:Wyjaśnij ten wpis|Więcej|Udostępnij|Przetłumacz wpis|Pokaż więcej|Zobacz więcej|Pokaż ten wątek|Show more|ALT|GIF|\d+:\d{2})$/i;

        while (end > start) {
            const tail = lines[end - 1];
            if (
                !tail ||
                metricTexts.has(tail) ||
                countOnlyRe.test(tail) ||
                footerNoiseRe.test(tail)
            ) {
                end -= 1;
                continue;
            }
            break;
        }

        const bodyText = lines.slice(start, end).join("\n").trim();
        return { authorName, text: bodyText, isReply };
    }

    function extractStatusInfo(article, mainUser) {
        const outerAnchors = outerElements(article, 'a[href*="/status/"]', mainUser);
        const allAnchors = Array.from(article.querySelectorAll('a[href*="/status/"]'));
        const pool = outerAnchors.length ? outerAnchors : allAnchors;

        let fallbackMatch = null;
        let fallbackAnchor = null;

        for (const a of pool) {
            let pathname = "";
            try {
                pathname = new URL(a.href, window.location.origin).pathname;
            } catch {
                pathname = a.getAttribute("href") || "";
            }
            const mm = pathname.match(/\/([^/?#]+)\/status\/(\d+)/);
            if (!mm) continue;
            if (/^\/[^/?#]+\/status\/\d+\/?$/.test(pathname)) {
                return { anchor: a, handle: mm[1], tweetId: mm[2] };
            }
            if (!fallbackMatch) {
                fallbackMatch = mm;
                fallbackAnchor = a;
            }
        }
        if (fallbackMatch) {
            return { anchor: fallbackAnchor, handle: fallbackMatch[1], tweetId: fallbackMatch[2] };
        }
        return null;
    }

    function scrapeVisible(store) {
        let added = 0;
        let updated = 0;
        const currentQuery = new URLSearchParams(window.location.search).get("q") || "";
        let articles = document.querySelectorAll('article[data-testid="tweet"]');
        if (!articles.length) {
            articles = document.querySelectorAll("article");
        }

        articles.forEach((article) => {
            const mainUser = article.querySelector('[data-testid="User-Name"]');
            const statusInfo = extractStatusInfo(article, mainUser);
            if (!statusInfo) return;

            let { handle, tweetId, anchor } = statusInfo;
            if (handle === "i" && mainUser) {
                const handleMatch = (mainUser.innerText || "").match(/@([A-Za-z0-9_]+)/);
                if (handleMatch) handle = handleMatch[1];
            }

            const timeEl =
                (anchor && anchor.querySelector("time")) ||
                outerElements(article, "time", mainUser)[0] ||
                article.querySelector("time");
            const timestamp = (timeEl && timeEl.getAttribute("datetime")) || snowflakeToIso(tweetId);

            const viewsInfo = readMetricInfo(
                article,
                [
                    'a[href*="/analytics"]',
                    '[aria-label*="wyświetle" i]',
                    '[aria-label*="view" i]',
                ],
                mainUser
            );
            const repliesInfo = readMetricInfo(
                article,
                [
                    '[data-testid="reply"]',
                    'button[aria-label*="odpowied" i]',
                    'a[aria-label*="odpowied" i]',
                    'button[aria-label*="repl" i]',
                ],
                mainUser
            );
            const repostsInfo = readMetricInfo(
                article,
                [
                    '[data-testid="retweet"]',
                    '[data-testid="unretweet"]',
                    'button[aria-label*="podane dalej" i]',
                    'button[aria-label*="podaj wpis dalej" i]',
                    'button[aria-label*="podaj dalej" i]',
                    'button[aria-label*="repost" i]',
                    'button[aria-label*="retweet" i]',
                ],
                mainUser
            );
            const likesInfo = readMetricInfo(
                article,
                [
                    '[data-testid="like"]',
                    '[data-testid="unlike"]',
                    'button[aria-label*="polubi" i]',
                    'button[aria-label*="like" i]',
                ],
                mainUser
            );
            const bookmarksInfo = readMetricInfo(
                article,
                [
                    '[data-testid="bookmark"]',
                    '[data-testid="removeBookmark"]',
                    'button[aria-label*="zakład" i]',
                    'button[aria-label*="bookmark" i]',
                ],
                mainUser
            );

            const metricTexts = new Set(
                [
                    viewsInfo.rawText,
                    repliesInfo.rawText,
                    repostsInfo.rawText,
                    likesInfo.rawText,
                    bookmarksInfo.rawText,
                ].filter(Boolean)
            );

            const fallbackParsed = extractBodyFromInnerText(
                article.innerText || "",
                handle,
                metricTexts
            );

            const authorName = mainUser
                ? (mainUser.innerText || "").split("\n")[0].trim()
                : fallbackParsed.authorName;

            const textEl = outerElements(article, '[data-testid="tweetText"]', mainUser)[0];
            const text = textEl ? textEl.innerText.trim() : fallbackParsed.text;

            const domTags = Array.from(article.querySelectorAll('a[href*="/hashtag/"]')).map(
                (a) => a.innerText.trim().toLowerCase()
            );
            const textTags = (text.match(/#[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+/gi) || []).map((t) =>
                t.toLowerCase()
            );
            const hashtags = Array.from(new Set([...domTags, ...textTags])).filter(Boolean);

            const isReply =
                fallbackParsed.isReply ||
                /W odpowiedzi do|Odpowiadanie|Replying to/i.test(
                    (article.innerText || "").slice(0, 200)
                );
            const hasMedia =
                outerElements(
                    article,
                    '[data-testid="tweetPhoto"], [data-testid="videoPlayer"], img[src*="pbs.twimg.com/media"], video',
                    mainUser
                ).length > 0;

            const rec = {
                tweet_id: tweetId,
                url: `https://x.com/${handle}/status/${tweetId}`,
                author_handle: handle,
                author_name: authorName,
                timestamp,
                text,
                hashtags,
                views: viewsInfo.count,
                replies: repliesInfo.count,
                reposts: repostsInfo.count,
                likes: likesInfo.count,
                bookmarks: bookmarksInfo.count,
                is_reply: isReply,
                has_media: hasMedia,
                queries: currentQuery ? [currentQuery] : [],
            };

            const prev = store[tweetId];
            if (!prev) {
                store[tweetId] = rec;
                added += 1;
            } else {
                const mergedQueries = Array.from(
                    new Set([...(prev.queries || []), ...rec.queries])
                );
                if (!prev.text && rec.text) {
                    added += 1;
                }
                store[tweetId] = {
                    ...prev,
                    ...rec,
                    author_name:
                        rec.author_name && rec.author_name !== rec.author_handle
                            ? rec.author_name
                            : prev.author_name,
                    text: rec.text || prev.text,
                    hashtags: rec.hashtags.length ? rec.hashtags : prev.hashtags,
                    views: Math.max(prev.views || 0, rec.views),
                    replies: Math.max(prev.replies || 0, rec.replies),
                    reposts: Math.max(prev.reposts || 0, rec.reposts),
                    likes: Math.max(prev.likes || 0, rec.likes),
                    bookmarks: Math.max(prev.bookmarks || 0, rec.bookmarks),
                    queries: mergedQueries,
                };
                updated += 1;
            }
        });

        saveStore(store);
        const totalNow = Object.keys(store).length;
        if (articles.length > 0 && totalNow === 0 && !window.__bunkierWarned) {
            window.__bunkierWarned = true;
            const sampleHrefs = Array.from(articles[0].querySelectorAll("a")).map((a) =>
                a.getAttribute("href")
            );
            console.warn("[Bunkier Debug] Widoczne <article>, ale 0 sparsowano. Linki[0]:", sampleHrefs);
        }
        return {
            added,
            updated,
            total: totalNow,
            visible: articles.length,
        };
    }

    function buildPayload(store) {
        const tweets = Object.values(store).sort((a, b) =>
            (a.timestamp || "").localeCompare(b.timestamp || "")
        );
        return {
            exported_at: new Date().toISOString(),
            total_collected: tweets.length,
            tweets,
        };
    }

    function downloadJson(store) {
        const payload = JSON.stringify(buildPayload(store), null, 2);
        const blob = new Blob([payload], { type: "application/json;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "x_bunkier_raw.json";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    // Stop previous instance if re-run
    if (window.__bunkierTimer) {
        clearInterval(window.__bunkierTimer);
        window.__bunkierTimer = null;
    }
    const oldHud = document.getElementById(HUD_ID);
    if (oldHud) oldHud.remove();

    const store = loadStore();
    let running = true;
    let idleTicks = 0;
    let lastScrollH = 0;

    // Build CSP-safe floating HUD (top-right so docked DevTools never hides it)
    const hud = document.createElement("div");
    hud.id = HUD_ID;
    hud.style.cssText =
        "position:fixed;top:72px;right:20px;z-index:999999;background:#0a0a0c;color:#fff;border:2px solid #ff0033;border-radius:10px;padding:12px 14px;font-family:system-ui,-apple-system,sans-serif;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.75);min-width:270px;";

    const titleEl = document.createElement("div");
    titleEl.textContent = "#BUNKIER X COLLECTOR";
    titleEl.style.cssText = "font-weight:800;color:#ff0033;letter-spacing:0.5px;margin-bottom:6px;";
    hud.appendChild(titleEl);

    const statusEl = document.createElement("div");
    statusEl.style.cssText = "color:#e4e4e7;margin-bottom:10px;line-height:1.4;";
    hud.appendChild(statusEl);

    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:6px;flex-wrap:wrap;";
    hud.appendChild(btnRow);

    function makeBtn(label, bg) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.style.cssText = `background:${bg};color:#fff;border:none;border-radius:6px;padding:6px 10px;font-size:12px;font-weight:700;cursor:pointer;`;
        return b;
    }

    const btnToggle = makeBtn("Pauza", "#3f3f46");
    const btnDownload = makeBtn("Pobierz JSON", "#ff0033");
    const btnCopy = makeBtn("Kopiuj JSON", "#2563eb");
    const btnReset = makeBtn("Wyczyść", "#18181b");
    btnReset.style.border = "1px solid #3f3f46";
    btnRow.append(btnToggle, btnDownload, btnCopy, btnReset);
    document.body.appendChild(hud);

    function refreshStatus(info, stateLabel) {
        const vis = info.visible !== undefined ? ` • DOM: ${info.visible}` : "";
        statusEl.textContent = `${stateLabel} • Zebrano: ${info.total} postów (+${info.added})${vis}`;
    }

    btnToggle.addEventListener("click", () => {
        running = !running;
        btnToggle.textContent = running ? "Pauza" : "Wznów";
        if (!running) {
            const info = scrapeVisible(store);
            refreshStatus(info, "Zatrzymano");
        }
    });

    btnDownload.addEventListener("click", () => {
        const info = scrapeVisible(store);
        downloadJson(store);
        refreshStatus(info, "Pobrano JSON");
    });

    btnCopy.addEventListener("click", async () => {
        const info = scrapeVisible(store);
        try {
            await navigator.clipboard.writeText(JSON.stringify(buildPayload(store), null, 2));
            refreshStatus(info, "Skopiowano JSON");
        } catch (err) {
            console.error("[Bunkier X] Clipboard error:", err);
            refreshStatus(info, "Użyj Pobierz JSON");
        }
    });

    btnReset.addEventListener("click", () => {
        if (window.confirm("Wyczyścić zebraną pamięć postów #bunkier z localStorage?")) {
            localStorage.removeItem(STORAGE_KEY);
            Object.keys(store).forEach((k) => delete store[k]);
            idleTicks = 0;
            refreshStatus({ added: 0, total: 0 }, "Wyczyszczono");
        }
    });

    const initial = scrapeVisible(store);
    refreshStatus(initial, "Scrollowanie");
    console.info(
        `%c #BUNKIER X COLLECTOR OK (widoczne na ekranie: ${initial.visible}, zebrano: ${initial.total}) `,
        "background:#ff0033;color:#fff;padding:4px 8px;font-weight:bold;border-radius:4px;"
    );
    const firstRec = Object.values(store).slice(-1)[0];
    if (firstRec) {
        console.info("[Bunkier Sample]", {
            author: "@" + firstRec.author_handle,
            text: firstRec.text.slice(0, 80),
            views: firstRec.views,
            likes: firstRec.likes,
            reposts: firstRec.reposts,
            replies: firstRec.replies,
        });
    }

    window.__bunkierTimer = setInterval(() => {
        if (!running) return;
        const info = scrapeVisible(store);
        const curScrollH = document.documentElement.scrollHeight;

        if (info.added === 0 && curScrollH === lastScrollH) {
            idleTicks += 1;
        } else {
            idleTicks = 0;
        }
        lastScrollH = curScrollH;

        if (idleTicks >= 5) {
            running = false;
            btnToggle.textContent = "Wznów";
            refreshStatus(info, "Koniec wyników");
            return;
        }

        refreshStatus(info, "Scrollowanie");
        window.scrollBy({ top: 950, behavior: "smooth" });
    }, 2200);

    window.__bunkier = {
        scrape: () => scrapeVisible(store),
        download: () => downloadJson(store),
        count: () => Object.keys(store).length,
        clear: () => {
            localStorage.removeItem(STORAGE_KEY);
            Object.keys(store).forEach((k) => delete store[k]);
        },
    };
})();
