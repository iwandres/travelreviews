/**
 * PunFiction: 1-Star Travel Reviews - Core Gameplay Application
 * 
 * DESIGN & DEPLOYMENT ARCHITECTURE:
 * 
 * 1. Environment Routing:
 *    - The client detects its platform context (Itch.io sandbox, CrazyGames portal, GitHub Pages, or localhost).
 *    - 'isItch': Matches 'itch.io', 'itch.zone', '.hwcdn.net', 'itch.im', or parent frame referrers.
 *    - 'isCrazyGames': True on portal frames, excluding localhost, github, and itch.
 * 
 * 2. Layout & Shift Prevention:
 *    - Main wrapper (.main-layout-container) uses justify-content: flex-start on small/iframe viewports.
 *      This anchors the game header to a static 20px padding-top and prevents loading shifts.
 *    - Google AdSense is loaded dynamically ONLY on production domain 'iwandres.github.io' to prevent
 *      Auto Ads from injecting headers and shifting layouts on Itch.io or CrazyGames.
 *    - The desktop sidebar ad container (.desktop-sidebar-ad) is conditionally hidden in Itch.io/CrazyGames.
 * 
 * 3. Accent Color Calculation (Cinema Gold & Indigo Rule):
 *    - Challenges with Orange/Yellow hues (startHue between 25 and 95) dynamically use a deep Indigo accent.
 *    - All other challenges (warm/cool hues) use a bright Cinema Gold accent for high contrast.
 * 
 * 4. CrazyGames SDK v3 Integration:
 *    - Ad Routing: Hint 4 (Vowel Rush) triggers crazySDK.ad.requestAd('rewarded') and victory triggers 'midgame' ads.
 *    - Game State Tracking: gameplayStart() runs when loading level is finished; gameplayStop() runs on victory.
 */

// Core Constants & CDN Paths
const GITHUB_REPO_URL = "https://raw.githubusercontent.com/iwandres/travelreviews/main/backend";
const BACKEND_API_URL = "https://punfiction.onrender.com";
const START_DATE_PT = new Date("2026-07-04T02:00:00-07:00"); // Launch date: 2am Pacific Time

// Pre-warm the backend Render service in the background as early as possible
function prewarmBackend() {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) return;
    
    console.log("Initiating asynchronous backend pre-warm ping...");
    fetch(`${BACKEND_API_URL}/api/travelreviews/records?puzzle_number=001`, { mode: 'cors' })
        .then(res => {
            if (res.ok) {
                console.log("Render backend container warmed up and awake!");
            }
        })
        .catch(err => {
            console.log("Render backend pre-warm ping sent, warming up in background.");
        });
}

// Fetch utility wrapper supporting customized millisecond execution timeout
async function fetchWithTimeout(resource, options = {}) {
    const { timeout = 3500 } = options;
    
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(resource, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

// Game State
let puzzles = [];
let todayChallenge = null;
let yesterdayChallenge = null;
let isViewingPrevious = false;
let activeChallenge = null; // Currently playing challenge
let naturalTodayIndex = 1; // Global scheduling active puzzle number
let isPreviewMode = false;
let hint3Active = false; // Flag for Hint 3 (first letters populated)
let hint4Active = false; // Flag for Hint 4 (vowels populated)
let lockedInIndices = new Set(); // indices of correct letters locked in by player attempts
let animateVowelRush = false; // Flag to trigger Hint 4 vowel animation once on reveal
let hintsUsed = 0; // Number of progressive hints used
let activeRewardedEvent = null;
let rewardedSlot = null;
let streakAnimationPlayed = false;

let isCrazyGames = false;
let isItch = false;
let crazySDK = null;

async function initCrazyGamesSDK() {
    if (typeof window.CrazyGames !== 'undefined') {
        try {
            await window.CrazyGames.SDK.init();
            crazySDK = window.CrazyGames.SDK;
            console.log("CrazyGames SDK v3 initialized successfully.");
        } catch (e) {
            console.error("CrazyGames SDK initialization failed:", e);
        }
    } else {
        console.warn("CrazyGames SDK script not loaded yet. Retrying in 500ms...");
        setTimeout(initCrazyGamesSDK, 500);
    }
}

let currentLevel = 1; // 1 to 3 = thematic levels, 4 = boss level, 5 = victory screen
let inventory = []; // accumulated target words
let currentPuzzleIndex = 0; // index in local puzzles array
let activeFetchedFromCDN = false; // flag to trace assets loading
let allTelemetry = null; // cached telemetry stats for all puzzles
let telemetryFetchSucceeded = false; // flag indicating whether fetch succeeded
let telemetryStartSent = false; // flag to ensure start event is only sent once per session on interaction

// DOM Elements Mapping
const screens = {
    game: document.getElementById('game-screen'),
    victory: document.getElementById('victory-screen')
};

const ui = {
    challengeHeader: document.getElementById('challenge-header'),
    challengeHeaderVictory: document.getElementById('challenge-header-victory'),
    questionLabel: document.getElementById('question-label'),
    bossPosterWrapper: document.getElementById('boss-poster-wrapper'),
    bossPosterImg: document.getElementById('boss-poster-img'),
    mysteryBanner: document.getElementById('mystery-banner'),
    quoteDisplay: document.getElementById('quote-display'),
    pitchDisplay: document.getElementById('pitch-display'),
    guessSlotsContainer: document.getElementById('guess-slots-container'),
    guessInput: document.getElementById('guess-input'),
    guessForm: document.getElementById('guess-form'),
    feedbackMsg: document.getElementById('feedback-msg'),
    
    // Progressive hints
    btnShowHint1: document.getElementById('btn-show-hint1'),
    btnShowHint2: document.getElementById('btn-show-hint2'),
    btnShowHint3: document.getElementById('btn-show-hint3'),
    btnShowHint4: document.getElementById('btn-show-hint4'),
    hintDisplayBox: document.getElementById('hint-display-box'),
    movieHint: document.getElementById('movie-hint'),
    hintMovieSection: document.getElementById('section-hint-movie'),
    hintRhymeSection: document.getElementById('section-hint-rhyme'),
    hintLettersSection: document.getElementById('section-hint-letters'),
    hintVowelsSection: document.getElementById('section-hint-vowels'),
    lettersHint: document.getElementById('letters-hint'),
    btnSubmit: document.getElementById('btn-submit'),
    
    // Victory elements
    victoryPosterImg: document.getElementById('victory-poster-img'),
    finalBossTitle: document.getElementById('final-boss-title'),
    finalBossMovie: document.getElementById('final-boss-movie'),
    linkWikipedia: document.getElementById('link-wikipedia'),
    linkMaps: document.getElementById('link-maps'),
    finalBossPitch: document.getElementById('final-boss-pitch')
};
 
// ================= INITIALIZATION & SCHEDULING =================
 
window.onload = async () => {
    // Migrate local storage keys from tourist_traps_* to travelreviews_*
    const keysToMigrate = [
        'solved_puzzles',
        'solved_hints',
        'attempted_puzzles',
        'puzzle_attempts',
        'max_streak',
        'profile_id'
    ];
    try {
        keysToMigrate.forEach(k => {
            const oldVal = localStorage.getItem('tourist_traps_' + k);
            if (oldVal !== null) {
                if (localStorage.getItem('travelreviews_' + k) === null) {
                    localStorage.setItem('travelreviews_' + k, oldVal);
                }
                localStorage.removeItem('tourist_traps_' + k);
            }
        });
    } catch (e) {
        console.error("Local storage migration error:", e);
    }

    // Detect environment (CrazyGames, itch.io, or standard play)
    const hostname = window.location.hostname;
    const referrer = document.referrer || "";
    const isIframe = window.self !== window.top;
    
    // Check for local development or explicit preview mode query params
    const urlParams = new URLSearchParams(window.location.search);
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';
    isPreviewMode = isLocal || 
                    urlParams.get('preview') === 'true' || 
                    urlParams.get('playtest') === 'true' || 
                    urlParams.get('dev') === 'true';
    isItch = hostname.includes('itch.io') || 
             hostname.includes('itch.zone') || 
             hostname.includes('hwcdn.net') || 
             hostname.includes('itch.im') || 
             hostname.includes('newgrounds.com') || 
             hostname.includes('ungrounded.net') || 
             window.location.href.includes('itch.io') ||
             window.location.href.includes('newgrounds.com') ||
             (isIframe && (
                 referrer.includes('itch.io') || 
                 referrer.includes('itch.zone') || 
                 referrer.includes('newgrounds.com')
             ));
             
    isCrazyGames = !isItch && 
                   !hostname.includes('github.io') && 
                   !hostname.includes('punfiction.io') && 
                   !hostname.includes('localhost') && 
                   !hostname.includes('127.0.0.1');
                   
    console.log("Environment detection: isItch =", isItch, ", isCrazyGames =", isCrazyGames, ", hostname =", hostname, ", referrer =", referrer);
    
    if (isCrazyGames) {
        document.body.classList.add('crazygames-env');
        await initCrazyGamesSDK();
    }
    if (isItch) {
        document.body.classList.add('itch-env');
    }

    // Load Google AdSense only on the production GitHub Pages domain or custom domain
    if (hostname === 'iwandres.github.io' || hostname === 'punfiction.io') {
        const adsenseScript = document.createElement('script');
        adsenseScript.async = true;
        adsenseScript.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1900802133351015';
        adsenseScript.crossOrigin = 'anonymous';
        document.head.appendChild(adsenseScript);
    }

    // 0. Wake up the Render container in the background as early as possible
    prewarmBackend();

    // 1. Setup UI bindings
    const appTitle = document.getElementById('app-title');
    if (appTitle) {
        appTitle.onclick = () => {
            if (todayChallenge) {
                startGame(todayChallenge);
                history.replaceState(null, "", `?challenge=${todayChallenge.puzzle_number}`);
            }
        };
    }
    document.getElementById('btn-victory-lobby').onclick = () => startGame(todayChallenge);
    document.getElementById('btn-share-score').onclick = shareSolvedScore;
    const prevBanner = document.getElementById('previous-banner');
    if (prevBanner) {
        prevBanner.onclick = () => {
            viewPreviousChallenge();
        };
    }
    const giveUpBtn = document.getElementById('btn-give-up');
    if (giveUpBtn) {
        giveUpBtn.onclick = (e) => {
            e.preventDefault();
            giveUpChallenge();
        };
    }
    ui.guessForm.onsubmit = (e) => {
        e.preventDefault();
        handleGuessSubmit();
    };
    ui.guessInput.onkeydown = (e) => {
        if (e.key === 'Backspace') {
            // Snappy rendering fallback on backspace
            setTimeout(renderGuessSlots, 0);
        }
    };
    ui.guessInput.oninput = handleGuessInput;
    
    let keyboardFocusTimeout = null;
    ui.guessInput.addEventListener('focus', () => {
        if (keyboardFocusTimeout) {
            clearTimeout(keyboardFocusTimeout);
            keyboardFocusTimeout = null;
        }
        document.body.classList.add('keyboard-focused');
        
        // Multi-stage scrolling to handle different keyboard animation speeds across mobile devices
        if (window.innerWidth < 768) {
            const scrollSlots = () => {
                if (ui.guessSlotsContainer) {
                    ui.guessSlotsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            };
            setTimeout(scrollSlots, 100);
            setTimeout(scrollSlots, 300);
            setTimeout(scrollSlots, 500);
        }
    });
    ui.guessInput.addEventListener('blur', () => {
        keyboardFocusTimeout = setTimeout(() => {
            document.body.classList.remove('keyboard-focused');
            keyboardFocusTimeout = null;
        }, 150);
    });
    if (ui.guessSlotsContainer) {
        ui.guessSlotsContainer.onclick = () => ui.guessInput.focus({ preventScroll: true });
    }
    ui.btnShowHint1.onclick = revealHint1;
    ui.btnShowHint2.onclick = revealHint2;
    ui.btnShowHint3.onclick = revealHint3;
    ui.btnShowHint4.onclick = () => {
        if (isCrazyGames && typeof window.CrazyGames !== 'undefined') {
            console.log("Triggering CrazyGames rewarded ad for Hint 4...");
            window.CrazyGames.SDK.ad.requestAd('rewarded', {
                adStarted: () => {
                    console.log("CrazyGames ad started");
                },
                adError: (error) => {
                    console.error("CrazyGames ad error:", error);
                    revealHint4(); // Fallback so player isn't stuck
                },
                adFinished: () => {
                    console.log("CrazyGames ad finished successfully");
                    revealHint4(); // Grant reward
                }
            });
        } else if (activeRewardedEvent) {
            console.log("Triggering rewarded ad for Hint 4...");
            activeRewardedEvent.makeRewardedVisible();
        } else {
            console.log("No active rewarded event. Triggering offline fallback Vowel Rush!");
            revealHint4();
        }
    };

    if (!isCrazyGames) {
        // Google Publisher Tag (GPT) setup and event listeners
        window.googletag = window.googletag || { cmd: [] };
        googletag.cmd.push(() => {
            googletag.pubads().addEventListener('rewardedSlotReady', (event) => {
                console.log("Rewarded slot is ready.");
                activeRewardedEvent = event;
            });

            googletag.pubads().addEventListener('rewardedSlotGranted', (event) => {
                console.log("Rewarded slot reward granted. Unlocking Vowel Rush!");
                revealHint4();
            });

            googletag.pubads().addEventListener('rewardedSlotClosed', (event) => {
                console.log("Rewarded slot closed.");
                if (rewardedSlot) {
                    googletag.destroySlots([rewardedSlot]);
                    rewardedSlot = null;
                }
                activeRewardedEvent = null;
                requestNextRewardedAd();
            });

            googletag.pubads().addEventListener('rewardedSlotVideoCompleted', (event) => {
                console.log("Rewarded slot video completed.");
            });

            googletag.pubads().addEventListener('slotRenderEnded', (event) => {
                console.log("Slot render ended:", event.slot.getAdUnitPath(), {
                    isEmpty: event.isEmpty,
                    creativeId: event.creativeId,
                    lineItemId: event.lineItemId,
                    advertiserId: event.advertiserId
                });
            });

            googletag.enableServices();
        });
    }

    const prevBtn = document.getElementById('btn-prev-challenge');
    if (prevBtn) prevBtn.onclick = () => navigateChallenge(-1);
    const nextBtn = document.getElementById('btn-next-challenge');
    if (nextBtn) nextBtn.onclick = () => navigateChallenge(1);

    const prevBtnVic = document.getElementById('btn-prev-challenge-victory');
    if (prevBtnVic) prevBtnVic.onclick = () => navigateChallenge(-1);
    const nextBtnVic = document.getElementById('btn-next-challenge-victory');
    if (nextBtnVic) nextBtnVic.onclick = () => navigateChallenge(1);

    const toggleReviewsBtn = document.getElementById('btn-toggle-reviews');
    const finalBossQuote = document.getElementById('final-boss-quote');
    if (toggleReviewsBtn && finalBossQuote) {
        toggleReviewsBtn.onclick = () => {
            const isHidden = finalBossQuote.classList.toggle('hidden');
            toggleReviewsBtn.innerText = isHidden ? '1-Star Reviews ▼' : '1-Star Reviews ▲';
        };
    }

    const openStatsSelectModalWithTracking = () => {
        if (!statsSelectModal) return;
        statsSelectModal.classList.add('active');
        openStatsSelectModal();

        // Track stats view
        sendTelemetryEvent('click_stats');
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_view', {
                page_title: 'Global Stats',
                page_path: '/global-stats'
            });
        }
    };

    const openHowToPlayModalWithTracking = () => {
        if (!howToPlayModal) return;
        howToPlayModal.classList.add('active');

        // Track help view
        sendTelemetryEvent('click_help');
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_view', {
                page_title: 'How To Play',
                page_path: '/how-to-play'
            });
        }
    };

    const btnStatsSelectVic = document.getElementById('btn-stats-select-victory');
    if (btnStatsSelectVic) {
        btnStatsSelectVic.onclick = openStatsSelectModalWithTracking;
    }

    const btnHowToPlayVic = document.getElementById('btn-how-to-play-victory');
    if (btnHowToPlayVic) {
        btnHowToPlayVic.onclick = openHowToPlayModalWithTracking;
    }
 
    // Fullscreen Poster Modal bindings
    const posterModal = document.getElementById('poster-modal');
    const modalPosterImg = document.getElementById('modal-poster-img');
    const btnCloseModal = document.getElementById('btn-close-modal');

    if (ui.victoryPosterImg) {
        ui.victoryPosterImg.onclick = () => {
            if (ui.victoryPosterImg.src) {
                modalPosterImg.src = ui.victoryPosterImg.src;
                posterModal.classList.add('active');
            }
        };
    }

    if (btnCloseModal) {
        btnCloseModal.onclick = () => {
            posterModal.classList.remove('active');
        };
    }

    if (posterModal) {
        posterModal.onclick = (e) => {
            if (e.target === posterModal) {
                posterModal.classList.remove('active');
            }
        };
    }

    // How to Play Modal bindings
    const howToPlayModal = document.getElementById('how-to-play-modal');
    const btnHowToPlay = document.getElementById('btn-how-to-play');
    const btnCloseHowToPlay = document.getElementById('btn-close-how-to-play');

    if (btnHowToPlay) {
        btnHowToPlay.onclick = openHowToPlayModalWithTracking;
    }

    if (btnCloseHowToPlay) {
        btnCloseHowToPlay.onclick = () => {
            if (howToPlayModal) {
                howToPlayModal.classList.remove('active');
            }
        };
    }

    if (howToPlayModal) {
        howToPlayModal.onclick = (e) => {
            if (e.target === howToPlayModal) {
                howToPlayModal.classList.remove('active');
            }
        };
    }

    // Stats & Level Select Modal bindings
    const statsSelectModal = document.getElementById('stats-select-modal');
    const btnStatsSelect = document.getElementById('btn-stats-select');
    const btnCloseStatsSelect = document.getElementById('btn-close-stats-select');

    if (btnStatsSelect) {
        btnStatsSelect.onclick = openStatsSelectModalWithTracking;
    }

    if (btnCloseStatsSelect) {
        btnCloseStatsSelect.onclick = () => {
            if (statsSelectModal) {
                statsSelectModal.classList.remove('active');
            }
        };
    }

    if (statsSelectModal) {
        statsSelectModal.onclick = (e) => {
            if (e.target === statsSelectModal) {
                statsSelectModal.classList.remove('active');
            }
        };
    }

    // ================= USER SETTINGS & SYNC BINDINGS =================
    const settingsModal = document.getElementById('settings-modal');
    const btnSettings = document.getElementById('btn-settings');
    const btnSettingsVic = document.getElementById('btn-settings-victory');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const btnCopySyncCode = document.getElementById('btn-copy-sync-code');
    const btnSubmitSyncCode = document.getElementById('btn-submit-sync-code');
    const syncCodeInput = document.getElementById('sync-code-input');
    const btnResetProgress = document.getElementById('btn-reset-progress');

    const openSettingsModal = () => {
        if (!settingsModal) return;
        settingsModal.classList.add('active');

        // Track profile view
        sendTelemetryEvent('click_profile');
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_view', {
                page_title: 'Profile Settings',
                page_path: '/profile-settings'
            });
        }
        
        // 1. Load data
        const solvedList = getSolvedPuzzlesList();
        const attemptedList = getAttemptedPuzzles();
        
        // Ensure solved is a subset of attempted just in case of local storage discrepancies
        solvedList.forEach(p => attemptedList.add(p));
        
        const { currentStreak, maxStreak } = calculateStreakMetrics(solvedList);
        
        const totalAttempted = attemptedList.size;
        const totalSolved = solvedList.size;
        const accuracy = totalAttempted > 0 ? Math.round((totalSolved / totalAttempted) * 100) : 0;
        
        // 2. Populate UI elements
        document.getElementById('user-total-attempted').innerText = totalAttempted.toLocaleString();
        document.getElementById('user-total-solved').innerText = totalSolved.toLocaleString();
        document.getElementById('user-solve-accuracy').innerText = `${accuracy}%`;
        document.getElementById('user-current-streak').innerText = currentStreak.toLocaleString();
        document.getElementById('user-max-streak').innerText = maxStreak.toLocaleString();

        // Render 7-day streak calendar inside settings modal
        renderProfileStreakCalendar();
        
        const displayInput = document.getElementById('sync-code-display');
        if (displayInput) {
            displayInput.value = getOrGenerateProfileId();
        }

        // 3. Render Puzzle Directory lists
        const approved = getApprovedChallenges();
        const solvedPuzzles = [];
        const attemptedPuzzles = [];
        const unplayedPuzzles = [];
        
        approved.forEach(p => {
            const pNumStr = padPuzzleNumber(p.puzzle_number);
            if (solvedList.has(pNumStr)) {
                solvedPuzzles.push(p);
            } else if (attemptedList.has(pNumStr)) {
                attemptedPuzzles.push(p);
            } else {
                unplayedPuzzles.push(p);
            }
        });

        const renderBadgeList = (elementId, list, typeClass) => {
            const container = document.getElementById(elementId);
            if (!container) return;
            container.innerHTML = '';
            
            if (list.length === 0) {
                const emptySpan = document.createElement('span');
                emptySpan.style.fontSize = '0.85rem';
                emptySpan.style.color = '#7f8c8d';
                emptySpan.style.fontStyle = 'italic';
                emptySpan.innerText = 'None';
                container.appendChild(emptySpan);
                return;
            }
            
            list.forEach(p => {
                const btn = document.createElement('button');
                btn.className = `profile-puzzle-link ${typeClass}`;
                btn.innerText = parseInt(p.puzzle_number);
                btn.title = `Challenge #${p.puzzle_number}: "${p.boss_pun_title}"`;
                btn.onclick = () => {
                    startGame(p);
                    history.replaceState(null, "", `?challenge=${p.puzzle_number}`);
                    if (settingsModal) settingsModal.classList.remove('active');
                };
                container.appendChild(btn);
            });
        };
        
        renderBadgeList('profile-solved-list', solvedPuzzles, 'solved');
        renderBadgeList('profile-attempted-list', attemptedPuzzles, 'attempted');
        renderBadgeList('profile-unplayed-list', unplayedPuzzles, 'unplayed');
    };

    if (btnSettings) btnSettings.onclick = openSettingsModal;
    if (btnSettingsVic) btnSettingsVic.onclick = openSettingsModal;
    const headerStreakBadge = document.getElementById('header-streak-badge');
    if (headerStreakBadge) headerStreakBadge.onclick = openSettingsModal;

    if (btnCloseSettings) {
        btnCloseSettings.onclick = () => {
            if (settingsModal) settingsModal.classList.remove('active');
        };
    }

    if (settingsModal) {
        settingsModal.onclick = (e) => {
            if (e.target === settingsModal) {
                settingsModal.classList.remove('active');
            }
        };
    }

    if (btnCopySyncCode) {
        btnCopySyncCode.onclick = () => {
            const displayInput = document.getElementById('sync-code-display');
            if (displayInput && displayInput.value) {
                navigator.clipboard.writeText(displayInput.value).then(() => {
                    showToast("📋 Sync Code copied to clipboard!");
                }).catch(err => {
                    console.error("Failed copying code: ", err);
                });
            }
        };
    }

    if (btnSubmitSyncCode) {
        btnSubmitSyncCode.onclick = async () => {
            if (!syncCodeInput || !syncCodeInput.value.trim()) {
                showToast("⚠️ Please enter a valid Sync Code!");
                return;
            }
            btnSubmitSyncCode.disabled = true;
            btnSubmitSyncCode.innerText = "Syncing...";
            
            const success = await fetchAndMergeProfile(syncCodeInput.value);
            btnSubmitSyncCode.disabled = false;
            btnSubmitSyncCode.innerText = "Sync Device";
            
            if (success) {
                showToast("🔄 Progress synced successfully!");
                syncCodeInput.value = '';
                if (settingsModal) settingsModal.classList.remove('active');
                
                // Reload active challenge view with updated solved state
                if (activeChallenge) {
                    startGame(activeChallenge);
                }
            } else {
                showToast("❌ Sync failed! Invalid or expired code.");
            }
        };
    }

    if (btnResetProgress) {
        btnResetProgress.onclick = () => {
            const confirmReset = confirm("⚠️ Are you sure you want to reset all your progress? This will delete all your local solving statistics and cannot be undone.");
            if (confirmReset) {
                try {
                    localStorage.removeItem('travelreviews_solved_puzzles');
                    localStorage.removeItem('travelreviews_solved_hints');
                    localStorage.removeItem('travelreviews_attempted_puzzles');
                    localStorage.removeItem('travelreviews_puzzle_attempts');
                    localStorage.removeItem('travelreviews_max_streak');
                    showToast("🗑️ All progress has been reset.");
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } catch (e) {
                    console.error("Error clearing progress", e);
                }
            }
        };
    }

    // Listen for window resize to adjust slot sizes dynamically
    let stampResizeTimeout = null;
    window.addEventListener('resize', () => {
        if (screens.game.classList.contains('active')) {
            renderGuessSlots();
        }
        clearTimeout(stampResizeTimeout);
        stampResizeTimeout = setTimeout(() => {
            if (activeChallenge) {
                updateBackgroundStamps(activeChallenge.puzzle_number);
            }
        }, 200);
    });

    // 2. Fetch and synchronize puzzle database
    await loadPuzzleDatabase();

    // 3. Initialize hover-based daily streak tooltip for desktop users
    initStreakTooltip();
    initNextButtonVictoryTooltip();
    initWorldMapFeature();
    if (urlParams.get('view') === 'map') {
        openWorldMapModal();
    }
    
    // Update daily solve streak badge next to the app header
    updateHeaderStreak();
};

function getDaysElapsedSinceStart() {
    try {
        const now = new Date();
        const START_YEAR = 2026;
        const START_MONTH = 7; // July
        const START_DAY = 4;
        const START_HOUR = 2;

        const formatter = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/Los_Angeles",
            year: "numeric",
            month: "numeric",
            day: "numeric",
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            hour12: false
        });
        
        const parts = formatter.formatToParts(now);
        const partVal = (type) => parseInt(parts.find(p => p.type === type).value, 10);

        const yr = partVal("year");
        const mo = partVal("month");
        const dy = partVal("day");
        const hr = partVal("hour");
        const min = partVal("minute");
        const sec = partVal("second");

        const nowPTUtc = new Date(Date.UTC(yr, mo - 1, dy, hr, min, sec));
        const startPTUtc = new Date(Date.UTC(START_YEAR, START_MONTH - 1, START_DAY, START_HOUR, 0, 0));

        const diffMs = nowPTUtc.getTime() - startPTUtc.getTime();
        const days = Math.floor(diffMs / (24 * 60 * 60 * 1000));
        return Math.max(0, days);
    } catch (e) {
        console.error("Timezone calculation failed, falling back to local difference:", e);
        const now = new Date();
        const diffMs = now.getTime() - START_DATE_PT.getTime();
        return Math.max(0, Math.floor(diffMs / (24 * 60 * 60 * 1000)));
    }
}

function padPuzzleNumber(num) {
    return String(num).padStart(3, '0');
}

async function loadPuzzleDatabase() {
    let rawData = null;
    
    // Try fetching from public GitHub RAW content CDN first
    try {
        const cdnUrl = `${GITHUB_REPO_URL}/travelreviews_daily_games.json?t=${Date.now()}`;
        const res = await fetch(cdnUrl);
        if (res.ok) {
            rawData = await res.json();
            activeFetchedFromCDN = true;
            console.log("Loaded puzzle database from GitHub RAW CDN!");
        }
    } catch (e) {
        console.warn("Could not fetch from GitHub CDN, falling back to local server api...", e);
    }

    // Fallback to local server API (for local development or curation previews)
    if (!rawData) {
        try {
            const localUrl = `/api/puzzles?t=${Date.now()}`;
            const res = await fetch(localUrl);
            if (res.ok) {
                rawData = await res.json();
                activeFetchedFromCDN = false;
                console.log("Loaded puzzle database from Curation Local Server!");
            }
        } catch (e) {
            console.error("Critical: Failed to load daily challenges database from all sources.", e);
            showToast("Failed to load daily challenges. Curation server offline?", true);
            const appEl = document.getElementById('app');
            if (appEl) {
                appEl.classList.remove('app-loading');
            }
            return;
        }
    }

    puzzles = Array.isArray(rawData) ? rawData : [];

    // Filter only approved daily challenges that have valid puzzle numbers
    const approvedChallenges = puzzles.filter(p => p.status === 'approved' && p.puzzle_number);

    if (approvedChallenges.length === 0) {
        console.error("No approved daily challenges are active.");
        return;
    }

    // Sort approved challenges sequentially
    approvedChallenges.sort((a, b) => parseInt(a.puzzle_number) - parseInt(b.puzzle_number));

    // Calculate current scheduling indexes based on elapsed days since launch (updates at 2am PT)
    const daysElapsed = getDaysElapsedSinceStart();
    naturalTodayIndex = daysElapsed + 1;
    let currentDayIndex = naturalTodayIndex;

    // Check if player URL overrides day (e.g. ?day=001) for diagnostic playtesting
    const urlParams = new URLSearchParams(window.location.search);
    const dayOverride = isItch ? null : (urlParams.get('day') || urlParams.get('challenge'));
    let matchedOverride = null;

    if (dayOverride) {
        const parsedOverride = parseInt(dayOverride);
        // Security constraint: only allow loading historical or today's active challenges (<= naturalTodayIndex)
        if (isPreviewMode || (!isNaN(parsedOverride) && parsedOverride > 0 && parsedOverride <= naturalTodayIndex)) {
            matchedOverride = approvedChallenges.find(p => p.puzzle_number === padPuzzleNumber(dayOverride));
            if (matchedOverride) {
                currentDayIndex = parsedOverride;
            }
        } else {
            console.warn("Attempted to access locked future challenge: ", dayOverride);
            // Clean up the URL parameter to prevent spoofing
            history.replaceState(null, "", window.location.pathname);
        }
    }

    const todayChallengeStr = padPuzzleNumber(naturalTodayIndex);
    const yesterdayChallengeStr = padPuzzleNumber(naturalTodayIndex - 1);

    // Map challenges
    todayChallenge = approvedChallenges.find(p => p.puzzle_number === todayChallengeStr) || approvedChallenges[approvedChallenges.length - 1];
    yesterdayChallenge = approvedChallenges.find(p => p.puzzle_number === yesterdayChallengeStr) || null;

    if (matchedOverride) {
        console.log(`URL Parameter Override: Playing Challenge #${dayOverride}`);
        startGame(matchedOverride);
    } else {
        // Otherwise, start Today's challenge automatically on load!
        startGame(todayChallenge);
    }
}



// ================= LOCAL STORAGE PROGRESS TRACKING =================

function getSolvedPuzzlesList() {
    try {
        const data = localStorage.getItem('travelreviews_solved_puzzles');
        const list = data ? JSON.parse(data) : [];
        return new Set(list.map(p => padPuzzleNumber(p)));
    } catch (e) {
        return new Set();
    }
}

function getSolvedHintsMap() {
    try {
        const data = localStorage.getItem('travelreviews_solved_hints');
        const map = data ? JSON.parse(data) : {};
        const sanitized = {};
        Object.keys(map).forEach(k => {
            sanitized[padPuzzleNumber(k)] = map[k];
        });
        return sanitized;
    } catch (e) {
        return {};
    }
}

function savePuzzleSolved(puzzleNum) {
    try {
        const paddedNum = padPuzzleNumber(puzzleNum);
        const solved = getSolvedPuzzlesList();
        solved.add(paddedNum);
        localStorage.setItem('travelreviews_solved_puzzles', JSON.stringify([...solved]));
        
        // Save the number of hints used for this puzzle
        const solvedHints = getSolvedHintsMap();
        solvedHints[paddedNum] = hintsUsed;
        localStorage.setItem('travelreviews_solved_hints', JSON.stringify(solvedHints));

        // Push solved status to backend profile sync
        postUserProfile();

        // If this is today's puzzle, reset animation flag to trigger the celebration animation on solve
        const isToday = todayChallenge && paddedNum === padPuzzleNumber(todayChallenge.puzzle_number);
        if (isToday) {
            streakAnimationPlayed = false;
        }

        // Update daily solve streak badge next to the app header
        updateHeaderStreak();
    } catch (e) {
        console.error("Could not write solved progress to local storage", e);
    }
}

// Generate a profile sync ID (PF-XXXXXX)
function getOrGenerateProfileId() {
    try {
        let profileId = localStorage.getItem('travelreviews_profile_id');
        if (!profileId) {
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
            let randomCode = '';
            for (let i = 0; i < 6; i++) {
                randomCode += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            profileId = `PF-${randomCode}`;
            localStorage.setItem('travelreviews_profile_id', profileId);
        }
        return profileId;
    } catch (e) {
        return "PF-ERROR";
    }
}

function getAttemptedPuzzles() {
    try {
        const data = localStorage.getItem('travelreviews_attempted_puzzles');
        const list = data ? JSON.parse(data) : [];
        return new Set(list.map(p => padPuzzleNumber(p)));
    } catch (e) {
        return new Set();
    }
}

function getPuzzleAttemptsMap() {
    try {
        const data = localStorage.getItem('travelreviews_puzzle_attempts');
        const map = data ? JSON.parse(data) : {};
        const sanitized = {};
        Object.keys(map).forEach(k => {
            sanitized[padPuzzleNumber(k)] = parseInt(map[k]) || 0;
        });
        return sanitized;
    } catch (e) {
        return {};
    }
}

function incrementPuzzleAttempts(puzzleNum) {
    try {
        const paddedNum = padPuzzleNumber(puzzleNum);
        const attemptsMap = getPuzzleAttemptsMap();
        attemptsMap[paddedNum] = (attemptsMap[paddedNum] || 0) + 1;
        localStorage.setItem('travelreviews_puzzle_attempts', JSON.stringify(attemptsMap));
    } catch (e) {
        console.error("Could not write attempts progress to local storage", e);
    }
}

function savePuzzleAttempted(puzzleNum) {
    try {
        const paddedNum = padPuzzleNumber(puzzleNum);
        const attempted = getAttemptedPuzzles();
        if (!attempted.has(paddedNum)) {
            attempted.add(paddedNum);
            localStorage.setItem('travelreviews_attempted_puzzles', JSON.stringify([...attempted]));
            
            // Push attempted status to backend profile sync
            postUserProfile();
        }
    } catch (e) {
        console.error("Could not write attempted progress to local storage", e);
    }
}

// Dynamically calculate solved streak metrics
function calculateStreakMetrics(solvedList) {
    let currentStreak = 0;
    let maxStreak = 0;
    
    try {
        maxStreak = parseInt(localStorage.getItem('travelreviews_max_streak')) || 0;
    } catch (e) {}

    // Trace backwards starting from natural today
    if (naturalTodayIndex) {
        let checkDay = naturalTodayIndex;
        // If today is not solved, check if yesterday was solved to keep the streak active
        const todayStr = padPuzzleNumber(checkDay);
        const yesterdayStr = padPuzzleNumber(checkDay - 1);
        
        if (!solvedList.has(todayStr) && solvedList.has(yesterdayStr)) {
            checkDay = checkDay - 1; // start check from yesterday
        }
        
        while (checkDay > 0) {
            const dayStr = padPuzzleNumber(checkDay);
            if (solvedList.has(dayStr)) {
                currentStreak++;
                checkDay--;
            } else {
                break;
            }
        }
    }
    
    if (currentStreak > maxStreak) {
        maxStreak = currentStreak;
        try {
            localStorage.setItem('travelreviews_max_streak', maxStreak.toString());
        } catch (e) {}
    }
    
    return { currentStreak, maxStreak };
}

// Push user profile to database server
async function postUserProfile() {
    const profileId = getOrGenerateProfileId();
    if (profileId === "PF-ERROR") return;
    
    const solved = [...getSolvedPuzzlesList()];
    const hints = getSolvedHintsMap();
    const attempted = [...getAttemptedPuzzles()];
    const { maxStreak } = calculateStreakMetrics(new Set(solved));
    
    const payload = {
        profile_id: profileId,
        solved_puzzles: solved,
        solved_hints: hints,
        attempted_puzzles: attempted,
        max_streak: maxStreak
    };
    
    try {
        const userUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? '/api/user'
            : `${BACKEND_API_URL}/api/travelreviews/user`;
            
        await fetch(userUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            mode: 'cors'
        });
    } catch (e) {
        console.log("Offline or failed syncing user profile to server", e);
    }
}

// Fetch from server and merge progress
async function fetchAndMergeProfile(serverProfileId) {
    if (!serverProfileId || !serverProfileId.trim()) return false;
    
    try {
        const userUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? `/api/user?profile_id=${serverProfileId.trim().toUpperCase()}`
            : `${BACKEND_API_URL}/api/travelreviews/user?profile_id=${serverProfileId.trim().toUpperCase()}`;
            
        const res = await fetch(userUrl, {
            mode: 'cors'
        });
        if (!res.ok) return false;
        
        const data = await res.json();
        if (data.error) return false;
        
        // 1. Merge Solved Puzzles
        const localSolved = getSolvedPuzzlesList();
        const serverSolved = data.solved_puzzles || [];
        serverSolved.forEach(p => localSolved.add(padPuzzleNumber(p)));
        localStorage.setItem('travelreviews_solved_puzzles', JSON.stringify([...localSolved]));
        
        // 2. Merge Solved Hints (take minimum hints used)
        const localHints = getSolvedHintsMap();
        const serverHints = data.solved_hints || {};
        Object.keys(serverHints).forEach(p => {
            const paddedP = padPuzzleNumber(p);
            const serverH = serverHints[p];
            const localH = localHints[paddedP];
            if (localH === undefined || serverH < localH) {
                localHints[paddedP] = serverH;
            }
        });
        localStorage.setItem('travelreviews_solved_hints', JSON.stringify(localHints));
        
        // 3. Merge Attempted Puzzles
        const localAttempted = getAttemptedPuzzles();
        const serverAttempted = data.attempted_puzzles || [];
        serverAttempted.forEach(p => localAttempted.add(padPuzzleNumber(p)));
        localStorage.setItem('travelreviews_attempted_puzzles', JSON.stringify([...localAttempted]));
        
        // 4. Merge Max Streak
        let localMaxStreak = parseInt(localStorage.getItem('travelreviews_max_streak')) || 0;
        const serverMaxStreak = data.max_streak || 0;
        if (serverMaxStreak > localMaxStreak) {
            localStorage.setItem('travelreviews_max_streak', serverMaxStreak.toString());
        }
        
        // 5. Update local profile ID to the synced one
        localStorage.setItem('travelreviews_profile_id', serverProfileId.toUpperCase());
        
        // 6. Push merged state back to server to make it fully synchronous
        await postUserProfile();
        
        // Update daily solve streak badge next to the app header
        updateHeaderStreak();
        
        return true;
    } catch (e) {
        console.error("Failed merging profiles:", e);
        return false;
    }
}

// ================= GAMEPLAY ENGINE =================

function switchScreen(screenName) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[screenName].classList.add('active');
    
    // Manage Previous Answer banner visibility and auto-shrink animation
    const prevBanner = document.getElementById('previous-banner');
    if (prevBanner) {
        if (screenName === 'game') {
            const approved = getApprovedChallenges();
            if (activeChallenge && approved.length > 0) {
                const currentIndex = approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number);
                const isToday = todayChallenge && activeChallenge && activeChallenge.puzzle_number === todayChallenge.puzzle_number;
                if (currentIndex > 0 && isToday) {
                    prevBanner.classList.remove('hidden');
                    prevBanner.classList.remove('shrunk');
                    
                    if (!prevBanner.dataset.timeoutActive) {
                        prevBanner.dataset.timeoutActive = 'true';
                        setTimeout(() => {
                            if (screens.game.classList.contains('active')) {
                                prevBanner.classList.add('shrunk');
                            }
                            delete prevBanner.dataset.timeoutActive;
                        }, 5000);
                    }
                } else {
                    prevBanner.classList.add('hidden');
                }
            } else {
                prevBanner.classList.add('hidden');
            }
        } else {
            prevBanner.classList.add('hidden');
        }
    }
}



function startGame(challenge) {
    if (!challenge) return;
    if (isCrazyGames && typeof window.CrazyGames !== 'undefined') {
        try {
            window.CrazyGames.SDK.game.gameplayStart();
            console.log("CrazyGames gameplayStart signaled.");
        } catch (e) {
            console.warn("CrazyGames gameplayStart failed:", e);
        }
    }
    activeChallenge = challenge;
    isViewingPrevious = false;
    hint3Active = false;
    hint4Active = false;
    lockedInIndices = new Set();
    animateVowelRush = false;
    hintsUsed = 0;
    currentLevel = 4; // Start directly at Boss Level!
    inventory = [];
    telemetryStartSent = false; // Reset start telemetry flag for new session

    if (challenge.puzzle_number) {
        updateBackgroundGradient(challenge.puzzle_number);
    }

    const solvedList = getSolvedPuzzlesList();
    if (solvedList.has(challenge.puzzle_number)) {
        const solvedHints = getSolvedHintsMap();
        hintsUsed = solvedHints[challenge.puzzle_number] !== undefined ? solvedHints[challenge.puzzle_number] : 0;
        triggerVictory();
    } else {
        switchScreen('game');
        loadLevel();
    }

    // Update challenge navigation buttons
    updateChallengeNavButtons();

    // Reveal app once game loads
    const appEl = document.getElementById('app');
    if (appEl) {
        appEl.classList.remove('app-loading');
    }

    // Send virtual pageview to Google Analytics for the active challenge
    if (typeof gtag === 'function') {
        gtag('config', 'G-41EV4HJ1LH', {
            'page_title': `Challenge #${challenge.puzzle_number}`,
            'page_path': `${window.location.pathname}?challenge=${challenge.puzzle_number}`,
            'game_name': 'travel_reviews'
        });
    }
}

function getCorrectPosterUrl(urlPath) {
    if (!urlPath) return "https://placehold.co/140x210/111625/f8fafc?text=No+Poster";
    
    // Normalize urlPath to remove leading slash for subfolder-relative resolves
    const cleanPath = urlPath.startsWith('/') ? urlPath.substring(1) : urlPath;
    
    if (activeFetchedFromCDN) {
        // Load poster illustration from raw public GitHub CDN under the travelreviews subfolder
        const rawRepoUrl = "https://raw.githubusercontent.com/iwandres/travelreviews/main/travelreviews";
        return `${rawRepoUrl}/${cleanPath}`;
    }
    // Sandbox local wrapper load
    return cleanPath;
}

function getHighlightedPunnedQuote(punnedQuote, originalQuote) {
    if (!punnedQuote) return '"Quote Text Missing"';
    if (!originalQuote) return `"${punnedQuote}"`;

    const clean = (word) => word.toLowerCase().replace(/[^a-z0-9]/g, '');

    const pWords = punnedQuote.split(' ');
    const oWords = originalQuote.split(' ');

    const highlighted = pWords.map((word, idx) => {
        const oWord = oWords[idx] || '';
        if (clean(word) !== clean(oWord)) {
            return `<span class="rhyme-word">${word}</span>`;
        }
        return word;
    }).join(' ');

    return `"${highlighted}"`;
}

function updateBackgroundGradient(puzzleNum) {
    const num = parseInt(puzzleNum) || 1;
    
    const themes = [
        { name: 'ancient_ruins', bg: '#FCFAF2', end: '#EADCB9', accent: '#873600' },
        { name: 'natural_wonders', bg: '#F4FAF5', end: '#C7E9D0', accent: '#1E8449' },
        { name: 'historic_monuments', bg: '#FDFCEF', end: '#F9E79F', accent: '#B7950B' },
        { name: 'castles_cathedrals', bg: '#FAF4FC', end: '#E8D0F5', accent: '#7D3C98' },
        { name: 'bridges_canals', bg: '#F2F9FA', end: '#BEE5F0', accent: '#0E6655' },
        { name: 'streets_squares', bg: '#FCF6F2', end: '#FAD7C4', accent: '#BA4A00' },
        { name: 'modern_skyscrapers', bg: '#F3F7FD', end: '#CADDFE', accent: '#1B4F72' }
    ];
    
    let theme = null;
    if (activeChallenge && activeChallenge.page_theme) {
        theme = themes.find(t => t.name === activeChallenge.page_theme);
    }
    if (!theme) {
        theme = themes[(num - 1) % themes.length];
    }
    
    document.documentElement.style.setProperty('--bg-color', theme.bg);
    document.documentElement.style.setProperty('--bg-gradient-end', theme.end);
    document.documentElement.style.setProperty('--accent-main', theme.accent);
}

function updateBackgroundStamps(puzzleNum) {
    const num = parseInt(puzzleNum) || 1;
    
    const themes = [
        { name: 'ancient_ruins' },
        { name: 'natural_wonders' },
        { name: 'historic_monuments' },
        { name: 'castles_cathedrals' },
        { name: 'bridges_canals' },
        { name: 'streets_squares' },
        { name: 'modern_skyscrapers' }
    ];
    
    let themeName = null;
    if (activeChallenge && activeChallenge.page_theme) {
        themeName = activeChallenge.page_theme;
    }
    if (!themeName || !themes.some(t => t.name === themeName)) {
        themeName = themes[(num - 1) % themes.length].name;
    }
    
    const themeStamps = {
        'ancient_ruins': ['stamp_airmail.png', 'stamp_compass.png'],
        'natural_wonders': ['stamp_globe.png', 'stamp_anchor.png'],
        'historic_monuments': ['stamp_luggage.png', 'stamp_passport_entry.png'],
        'castles_cathedrals': ['stamp_cancelled.png', 'stamp_airplane.png'],
        'bridges_canals': ['stamp_compass.png', 'stamp_anchor.png'],
        'streets_squares': ['stamp_airmail.png', 'stamp_luggage.png'],
        'modern_skyscrapers': ['stamp_globe.png', 'stamp_airplane.png']
    };
    
    const files = themeStamps[themeName];
    if (!files) return;
    
    const leftUrl = getCorrectPosterUrl(`assets/stamps/${files[0]}`);
    const rightUrl = getCorrectPosterUrl(`assets/stamps/${files[1]}`);
    
    const container = document.getElementById('bg-stamps-container');
    if (!container) return;
    
    // Clear existing stamps
    container.innerHTML = '';
    
    // Deterministically vary positions and rotations per puzzle number
    const leftTop = 15 + ((num * 13) % 30); // 15% to 45%
    const leftShift = -70 + ((num * 91) % 40); // -70px to -30px
    const leftRot = -15 - ((num * 7) % 25); // -15 to -40 deg
    const leftScale = 0.9 + ((num % 3) * 0.05); // 0.9 to 1.0
    
    const rightBottom = 20 + ((num * 17) % 30); // 20% to 50%
    const rightShift = -70 + ((num * 73) % 40); // -70px to -30px
    const rightRot = 15 + ((num * 9) % 25); // 15 to 40 deg
    const rightScale = 0.9 + (((num + 1) % 3) * 0.05); // 0.9 to 1.0
    
    // Create Left Stamp
    const leftEl = document.createElement('div');
    leftEl.className = 'bg-stamp stamp-left';
    leftEl.style.backgroundImage = `url('${leftUrl}')`;
    
    leftEl.style.setProperty('--stamp-left-top', `${leftTop}%`);
    leftEl.style.setProperty('--stamp-left-left', `${leftShift}px`);
    leftEl.style.setProperty('--stamp-left-left-desktop', `calc(50% - 440px + ${leftShift + 60}px)`);
    leftEl.style.setProperty('--stamp-left-left-desktop-wide', `calc(50% - 500px + ${leftShift + 60}px)`);
    
    leftEl.style.opacity = '0';
    leftEl.style.transform = `rotate(0deg) scale(0.2)`;
    leftEl.style.transition = 'opacity 0.9s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.9s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
    leftEl.style.transitionDelay = '0s';
    
    container.appendChild(leftEl);
    
    // Create Right Stamp
    const rightEl = document.createElement('div');
    rightEl.className = 'bg-stamp stamp-right';
    rightEl.style.backgroundImage = `url('${rightUrl}')`;
    
    rightEl.style.setProperty('--stamp-right-bottom', `${rightBottom}%`);
    rightEl.style.setProperty('--stamp-right-right', `${rightShift}px`);
    rightEl.style.setProperty('--stamp-right-right-desktop', `calc(50% - 440px + ${rightShift + 60}px)`);
    rightEl.style.setProperty('--stamp-right-right-desktop-wide', `calc(50% - 500px + ${rightShift + 60}px)`);
    
    rightEl.style.opacity = '0';
    rightEl.style.transform = `rotate(0deg) scale(0.2)`;
    rightEl.style.transition = 'opacity 0.9s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.9s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
    rightEl.style.transitionDelay = '0.08s'; // Staggered entry
    
    container.appendChild(rightEl);
    
    // Trigger animation transitions
    requestAnimationFrame(() => {
        setTimeout(() => {
            leftEl.style.opacity = '0.18'; // Muted watermark opacity
            leftEl.style.transform = `rotate(${leftRot}deg) scale(${leftScale})`;
            
            rightEl.style.opacity = '0.18';
            rightEl.style.transform = `rotate(${rightRot}deg) scale(${rightScale})`;
        }, 30);
    });
}

function loadLevel() {
    if (activeChallenge && activeChallenge.puzzle_number) {
        updateBackgroundGradient(activeChallenge.puzzle_number);
        updateBackgroundStamps(activeChallenge.puzzle_number);
    }
    hint3Active = false;
    hint4Active = false;
    animateVowelRush = false;
    hintsUsed = 0;
    activeRewardedEvent = null;
    requestNextRewardedAd();

    ui.guessInput.value = '';
    ui.feedbackMsg.innerText = '';
    ui.feedbackMsg.className = 'feedback';

    if (ui.challengeHeader) {
        ui.challengeHeader.innerHTML = `<span class="challenge-label">Challenge</span> #<span class="level-indicator-num">${activeChallenge.puzzle_number}</span>`;
    }
    if (ui.challengeHeaderVictory) {
        ui.challengeHeaderVictory.innerHTML = `<span class="challenge-label">Challenge</span> #<span class="level-indicator-num">${activeChallenge.puzzle_number}</span>`;
    }

    // Reset progressive hints container expand state
    const hintContainer = document.querySelector('.hint-container');
    if (hintContainer) {
        hintContainer.classList.remove('collapsed');
    }

    // Reset progressive hints
    ui.btnShowHint1.classList.remove('hidden');
    ui.btnShowHint2.classList.add('hidden');
    ui.btnShowHint3.classList.add('hidden');
    ui.btnShowHint4.classList.add('hidden');

    if (ui.hintDisplayBox) ui.hintDisplayBox.classList.add('hidden');
    if (ui.hintMovieSection) ui.hintMovieSection.classList.add('hidden');
    if (ui.hintRhymeSection) ui.hintRhymeSection.classList.add('hidden');
    if (ui.hintLettersSection) ui.hintLettersSection.classList.add('hidden');
    if (ui.hintVowelsSection) ui.hintVowelsSection.classList.add('hidden');

    // --- PUZZLE DIRECT PLAY ---
    ui.questionLabel.innerText = "Guess the location pun!";
    
    // Prepare poster image but keep it hidden during active play
    const posterUrl = getCorrectPosterUrl(activeChallenge.boss_poster_url);
    ui.bossPosterImg.src = posterUrl;
    ui.bossPosterImg.className = "boss-poster-img sharp";
    ui.bossPosterWrapper.classList.add('hidden');
    ui.mysteryBanner.classList.add('hidden');

    ui.movieHint.innerText = activeChallenge.boss_original_title || "Unknown";
    
    // Hide quoteDisplay as Clue 1 is now embedded inside the review box
    if (ui.quoteDisplay) {
        ui.quoteDisplay.style.display = 'none';
    }
    
    // Hook up pitch Display to Review Header info and include Clue 1 body text
    const reviewerName = activeChallenge.reviewer_name || "AnonymousTraveler";
    const reviewTitle = activeChallenge.review_title || "Avoid at all costs!";
    const clue1Text = activeChallenge.clue1 || "Review Text Missing";
    ui.pitchDisplay.innerHTML = `
        <span style="color: #ff4757; display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; font-weight: 800;">1-Star Review</span>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-family: var(--font-body);">
            <span style="font-weight: 800; font-size: 0.9rem; color: #555;">@${reviewerName}</span>
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: #ff4757; border: 2px solid #ff4757; display: inline-block; box-sizing: border-box;"></span>
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: transparent; border: 2px solid #ff4757; display: inline-block; box-sizing: border-box;"></span>
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: transparent; border: 2px solid #ff4757; display: inline-block; box-sizing: border-box;"></span>
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: transparent; border: 2px solid #ff4757; display: inline-block; box-sizing: border-box;"></span>
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: transparent; border: 2px solid #ff4757; display: inline-block; box-sizing: border-box;"></span>
            </div>
        </div>
        <div style="font-weight: 800; font-size: 1.1rem; color: var(--border-color); line-height: 1.25; font-family: var(--font-body); margin-bottom: 10px;">${reviewTitle}</div>
        <div style="font-family: var(--font-body); font-size: 0.88rem; font-weight: 600; color: #444; line-height: 1.5; border-top: 1.5px solid rgba(0,0,0,0.06); padding-top: 10px;">"${clue1Text}"</div>
        <div id="additional-reviews-box" class="hidden"></div>
    `;

    // Setup input maxLength based on letters count in answer
    const prefilledIndices = getPrefilledIndices(activeChallenge.boss_pun_title);
    const letterCount = getTotalLettersCount(activeChallenge.boss_pun_title);
    ui.guessInput.maxLength = letterCount - prefilledIndices.length;

    // Render interactive blank slots
    renderGuessSlots();
    // Re-render after a short delay to ensure browser layout has stabilized (prevents mobile layout shifting)
    setTimeout(renderGuessSlots, 50);

    // Auto-focus the input on desktop to allow typing immediately on level load
    if (window.innerWidth >= 768) {
        setTimeout(() => {
            ui.guessInput.focus({ preventScroll: true });
        }, 100);
    }

    // Update give up option visibility on level load
    updateGiveUpButtonVisibility();
}

function revealHint1() {
    triggerStartTelemetry();
    ui.btnShowHint1.classList.add('hidden');
    
    // Populate and show additional reviews inside the 1-Star Review box
    const box = document.getElementById('additional-reviews-box');
    if (box) {
        box.classList.remove('hidden');
        box.innerHTML = `
            <div style="font-family: var(--font-body); font-size: 0.88rem; font-weight: 600; color: #444; line-height: 1.5; border-top: 1.5px solid rgba(0,0,0,0.06); padding-top: 10px; margin-top: 10px;">
                <strong>Review 2:</strong> "${activeChallenge.clue2 || 'Details missing.'}"
            </div>
            <div style="font-family: var(--font-body); font-size: 0.88rem; font-weight: 600; color: #444; line-height: 1.5; border-top: 1.5px solid rgba(0,0,0,0.06); padding-top: 10px; margin-top: 10px;">
                <strong>Review 3:</strong> "${activeChallenge.clue3 || 'Details missing.'}"
            </div>
        `;
    }
    
    ui.btnShowHint2.classList.remove('hidden'); // Unlock Hint 2 button
    hintsUsed = 1;
}

function revealHint2() {
    triggerStartTelemetry();
    ui.btnShowHint2.classList.add('hidden');
    
    // Reveal Hint 2 section (Real Location) inside the consolidated Hint Box
    if (ui.hintDisplayBox) ui.hintDisplayBox.classList.remove('hidden');
    if (ui.hintMovieSection) ui.hintMovieSection.classList.remove('hidden');
    
    ui.btnShowHint3.classList.remove('hidden'); // Unlock Hint 3 button
    hintsUsed = 2;
}

function revealHint3() {
    triggerStartTelemetry();
    ui.btnShowHint3.classList.add('hidden');
    if (ui.hintDisplayBox) ui.hintDisplayBox.classList.remove('hidden');
    if (ui.hintLettersSection) ui.hintLettersSection.classList.remove('hidden'); // Reveal First Letters section inside box
    
    // Unlock Hint 4 button (Vowel Rush!)
    ui.btnShowHint4.classList.remove('hidden');
    
    if (ui.lettersHint) {
        ui.lettersHint.innerText = activeChallenge.boss_hint2 || generateFirstLetterBlanks(activeChallenge.boss_pun_title);
    }

    hintsUsed = 3;

    // Activate prefilled first-letters mode
    hint3Active = true;

    // Recalculate input maxLength based on remaining letters to type
    const firstLetterIndices = getFirstLetterIndices(activeChallenge.boss_pun_title);
    const totalLetters = getTotalLettersCount(activeChallenge.boss_pun_title);
    ui.guessInput.maxLength = totalLetters - firstLetterIndices.length;

    // Clear input to allow fresh typing of remaining letters
    ui.guessInput.value = '';

    // Render slots immediately with prefilled letters in correct positions
    renderGuessSlots();

    // Auto-focus input on desktop (skip on mobile to prevent focus-mode styling from immediately hiding the unlocked hint)
    if (window.innerWidth >= 768) {
        setTimeout(() => {
            ui.guessInput.focus({ preventScroll: true });
        }, 100);
    }
}

function revealHint4() {
    triggerStartTelemetry();
    ui.btnShowHint4.classList.add('hidden');
    if (ui.hintDisplayBox) ui.hintDisplayBox.classList.remove('hidden');
    if (ui.hintVowelsSection) ui.hintVowelsSection.classList.remove('hidden'); // Reveal Vowel Rush section inside box
    
    // Gracefully collapse the progressive hint buttons container since all buttons are now hidden
    const hintContainer = document.querySelector('.hint-container');
    if (hintContainer) {
        hintContainer.classList.add('collapsed');
    }
    
    hintsUsed = 4;
    hint4Active = true;
    animateVowelRush = true;

    // Recalculate input maxLength based on remaining letters to type
    const totalLettersHint4 = getTotalLettersCount(activeChallenge.boss_pun_title);
    const prefilledIndicesHint4 = getPrefilledIndices(activeChallenge.boss_pun_title);
    ui.guessInput.maxLength = totalLettersHint4 - prefilledIndicesHint4.length;

    // Clear input to allow fresh typing of remaining letters
    ui.guessInput.value = '';

    // Render slots immediately with prefilled letters & vowels in correct positions
    renderGuessSlots();

    // Auto-focus input on desktop (skip on mobile to prevent focus-mode styling from immediately hiding the vowel rush reveal)
    if (window.innerWidth >= 768) {
        setTimeout(() => {
            ui.guessInput.focus({ preventScroll: true });
        }, 100);
    }
    
    // Check give up option when Hint 4 is revealed
    updateGiveUpButtonVisibility();
}

// Check if a character is a special accented letter not typeable on standard US keyboards
const isSpecialAccentedChar = (char) => {
    return /\p{L}/u.test(char) && !/[a-zA-Z]/.test(char);
};

// Count total letters including standard and special accented characters
function getTotalLettersCount(title) {
    let count = 0;
    for (let i = 0; i < title.length; i++) {
        if (/[a-zA-Z]/.test(title[i]) || isSpecialAccentedChar(title[i])) {
            count++;
        }
    }
    return count;
}

function generateFirstLetterBlanks(str) {
    if (!str) return "";
    return str.split(' ').map(word => {
        if (word.length === 0) return "";
        const firstLetter = word[0];
        const rest = word.slice(1).replace(/[a-zA-Z]/g, "_");
        return firstLetter + rest;
    }).join(' ');
}

// ================= INTERACTIVE CHAR-SLOT PUZZLE LOGIC =================

function handleGuessInput() {
    triggerStartTelemetry();
    const origVal = ui.guessInput.value;
    const sanitizedVal = origVal.replace(/[^a-zA-Z]/g, '');
    if (origVal !== sanitizedVal) {
        ui.guessInput.value = sanitizedVal;
    }
    renderGuessSlots();
}

function getFirstLetterIndices(title) {
    const indices = [];
    let letterIdx = 0;
    let inWord = false;
    
    for (let i = 0; i < title.length; i++) {
        const char = title[i];
        if (/[a-zA-Z]/.test(char) || isSpecialAccentedChar(char)) {
            if (!inWord) {
                indices.push(letterIdx);
                inWord = true;
            }
            letterIdx++;
        } else {
            if (char === ' ' || char === '-' || char === ':') {
                inWord = false;
            }
        }
    }
    return indices;
}

function getPrefilledIndices(title) {
    const indices = [];
    let letterIdx = 0;
    
    const firstLetterIndices = hint3Active ? getFirstLetterIndices(title) : [];
    
    for (let i = 0; i < title.length; i++) {
        const char = title[i];
        if (/[a-zA-Z]/.test(char) || isSpecialAccentedChar(char)) {
            const isFirstLetter = firstLetterIndices.includes(letterIdx);
            const isVowelChar = hint4Active && /[aeiouAEIOU]/.test(char);
            const isLocked = lockedInIndices && lockedInIndices.has(letterIdx);
            const isSpecial = isSpecialAccentedChar(char);
            if (isFirstLetter || isVowelChar || isLocked || isSpecial) {
                indices.push(letterIdx);
            }
            letterIdx++;
        }
    }
    return indices;
}

function getCompleteGuessString() {
    if (!activeChallenge) return '';
    const title = activeChallenge.boss_pun_title;
    const currentGuess = ui.guessInput.value;
    const prefilledIndices = getPrefilledIndices(title);
    
    let completeStr = '';
    let letterIdx = 0;
    let typedIdx = 0;
    
    for (let i = 0; i < title.length; i++) {
        const char = title[i];
        if (/[a-zA-Z]/.test(char) || isSpecialAccentedChar(char)) {
            if (prefilledIndices.includes(letterIdx)) {
                completeStr += char;
            } else {
                completeStr += currentGuess[typedIdx] || '';
                if (currentGuess[typedIdx]) typedIdx++;
            }
            letterIdx++;
        } else {
            completeStr += char;
        }
    }
    return completeStr;
}

function renderGuessSlots() {
    if (!activeChallenge) return;
    const title = activeChallenge.boss_pun_title;
    
    // Set dynamic maxLength
    const prefilledIndices = getPrefilledIndices(title);
    const totalLetters = getTotalLettersCount(title);
    ui.guessInput.maxLength = totalLetters - prefilledIndices.length;
    
    const currentGuess = ui.guessInput.value;
    
    if (!ui.guessSlotsContainer) return;

    // Calculate maximum word length (excluding separators/punctuation)
    let maxWordLength = 0;
    const words = title.split(/[\s\-:\.,;]+/);
    words.forEach(w => {
        let cleanW = '';
        for (let idx = 0; idx < w.length; idx++) {
            if (/[a-zA-Z]/.test(w[idx]) || isSpecialAccentedChar(w[idx])) {
                cleanW += w[idx];
            }
        }
        if (cleanW.length > maxWordLength) {
            maxWordLength = cleanW.length;
        }
    });

    // Measure container clientWidth, fallback to 380px if not loaded
    const containerWidth = ui.guessSlotsContainer.clientWidth || 380;

    // Calculate optimal W (default max 32px)
    const maxSlotWidth = 32;
    let W = maxSlotWidth;
    if (maxWordLength > 0) {
        const targetWidth = containerWidth - 16;
        const computedW = Math.floor(targetWidth / (1.2 * maxWordLength - 0.2));
        if (computedW < maxSlotWidth) {
            W = Math.max(16, computedW);
        }
    }

    // Set other variables proportionally
    const G = Math.round(W / 5);
    const H = Math.round(W * 1.3125);
    const F = (W / 20).toFixed(2) + 'rem';
    const spaceW = Math.round(W * 0.4375);
    
    let B = '3px';
    let S = '2px';
    if (W < 20) {
        B = '1.5px';
        S = '1px';
    } else if (W < 28) {
        B = '2px';
        S = '1.5px';
    }

    // Apply values to style variables
    ui.guessSlotsContainer.style.setProperty('--slot-width', `${W}px`);
    ui.guessSlotsContainer.style.setProperty('--slot-height', `${H}px`);
    ui.guessSlotsContainer.style.setProperty('--slot-font-size', F);
    ui.guessSlotsContainer.style.setProperty('--slot-gap', `${G}px`);
    ui.guessSlotsContainer.style.setProperty('--slot-space-width', `${spaceW}px`);
    ui.guessSlotsContainer.style.setProperty('--slot-border', `${B}`);
    ui.guessSlotsContainer.style.setProperty('--slot-shadow', `${S}`);

    let html = '';
    let activeHighlighted = false;
    
    const firstLetterIndices = hint3Active ? getFirstLetterIndices(title) : [];
    
    let letterIdx = 0; // index in the letter sequence of the title
    let typedIdx = 0;  // index in the user's typed guessInput string
    
    const separators = [' ', '-', ':', '.', ',', ';'];
    let i = 0;
    
    while (i < title.length) {
        const char = title[i];
        
        if (separators.includes(char)) {
            // Render separators outside of word containers to allow wrapping at separator boundaries
            if (char === ' ') {
                html += `<span class="guess-separator-space">&nbsp;</span>`;
            } else {
                html += `<span class="guess-separator-char">${char}</span>`;
            }
            i++;
        } else {
            // Collect all contiguous non-separator characters to form a word container
            let wordChars = '';
            while (i < title.length && !separators.includes(title[i])) {
                wordChars += title[i];
                i++;
            }
            
            let wordHtml = '';
            for (let j = 0; j < wordChars.length; j++) {
                const wChar = wordChars[j];
                if (/[a-zA-Z]/.test(wChar) || isSpecialAccentedChar(wChar)) {
                    const isPrefilled = prefilledIndices.includes(letterIdx);
                    const isLocked = lockedInIndices && lockedInIndices.has(letterIdx);
                    const isSpecial = isSpecialAccentedChar(wChar);
                    
                    let displayChar = '';
                    let isFilled = false;
                    let isPrefilledStyle = false;
                    let isLockedStyle = false;
                    let isSpecialStyle = false;
                    
                    if (isSpecial) {
                        displayChar = wChar;
                        isFilled = true;
                        isSpecialStyle = true;
                    } else if (isPrefilled && !isLocked) {
                        displayChar = wChar; // display the actual letter from the title
                        isFilled = true;
                        isPrefilledStyle = true;
                    } else if (isLocked) {
                        displayChar = wChar; // display the locked-in correct letter
                        isFilled = true;
                        isLockedStyle = true;
                    } else {
                        displayChar = currentGuess[typedIdx] || '';
                        if (displayChar !== '') {
                            isFilled = true;
                            typedIdx++;
                        }
                    }
                    
                    const isLetterActive = !isFilled && !activeHighlighted;
                    
                    let classes = 'guess-letter-slot';
                    if (isFilled) classes += ' filled';
                    if (isPrefilledStyle) classes += ' prefilled';
                    if (isLockedStyle) classes += ' locked-in';
                    if (isSpecialStyle) classes += ' special-accented';
                    if (isLetterActive) {
                        classes += ' active';
                        activeHighlighted = true;
                    }
                    
                    // Highlight Hint 4 newly-revealed vowels with the vowel-rush class for animation (only once on reveal!)
                    const isVowelReveal = animateVowelRush && isPrefilled && /[aeiouAEIOU]/.test(wChar) && !firstLetterIndices.includes(letterIdx);
                    if (isVowelReveal) {
                        classes += ' vowel-rush';
                    }
                    
                    wordHtml += `<span class="${classes}">${displayChar || '&nbsp;'}</span>`;
                    letterIdx++;
                } else {
                    // Non-letter characters within a word (e.g. apostrophes) are rendered inside the word container
                    wordHtml += `<span class="guess-separator-char">${wChar}</span>`;
                }
            }
            
            html += `<span class="guess-word">${wordHtml}</span>`;
        }
    }
    
    ui.guessSlotsContainer.innerHTML = html;
    
    // Reset vowel rush animation trigger so subsequent input/rendering does not repeat the animation
    animateVowelRush = false;
}

// Clean guesses to ignore minor editorial punctuation
const sanitizeText = (str) => {
    if (!str) return "";
    return str.toLowerCase().replace(/[^a-z]/g, '');
};

// Get the next active progressive hint button currently visible to the user
function getActiveHintButton() {
    const ids = ['btn-show-hint1', 'btn-show-hint2', 'btn-show-hint3', 'btn-show-hint4'];
    for (const id of ids) {
        const btn = document.getElementById(id);
        if (btn && !btn.classList.contains('hidden')) {
            return btn;
        }
    }
    return null;
}

// Triggers a scale nudge pulse animation on the active hint button to highlight it
function triggerHintNudge() {
    const activeBtn = getActiveHintButton();
    if (!activeBtn) return;
    
    // Remove the class first to reset the animation if it was already running
    activeBtn.classList.remove('hint-nudge-active');
    // Force a reflow to reset the animation state in the browser
    void activeBtn.offsetWidth;
    // Add the animation class
    activeBtn.classList.add('hint-nudge-active');
    
    // Clean up class when animation finishes
    activeBtn.addEventListener('animationend', () => {
        activeBtn.classList.remove('hint-nudge-active');
    }, { once: true });
}

function handleGuessSubmit() {
    if (!activeChallenge) return;
    triggerStartTelemetry();
    
    const completeGuess = getCompleteGuessString();
    if (!completeGuess.trim()) {
        shakeInput();
        return;
    }

    // Record attempt telemetry event!
    sendTelemetryEvent('attempt');

    // Increment local attempts counter!
    incrementPuzzleAttempts(activeChallenge.puzzle_number);

    const cleanGuess = sanitizeText(completeGuess);
    const cleanBossAnswer = sanitizeText(activeChallenge.boss_pun_title);

    if (cleanGuess === cleanBossAnswer) {
        savePuzzleSolved(activeChallenge.puzzle_number);
        sendTelemetryEvent('solve', hintsUsed); // Post solve telemetry
        triggerVictory();
    } else {
        // Lock in correct letters matched on this attempt
        const title = activeChallenge.boss_pun_title;
        let letterIdx = 0;
        for (let i = 0; i < title.length; i++) {
            const char = title[i];
            if (/[a-zA-Z]/.test(char) || isSpecialAccentedChar(char)) {
                const guessChar = completeGuess[i];
                if (guessChar && guessChar.toLowerCase() === char.toLowerCase()) {
                    lockedInIndices.add(letterIdx);
                }
                letterIdx++;
            }
        }

        ui.feedbackMsg.innerText = "Incorrect.  Try again!";
        ui.feedbackMsg.className = "feedback error";
        ui.guessInput.value = '';
        renderGuessSlots();
        shakeInput();
        setTimeout(triggerHintNudge, 1200);
        
        // Auto-refocus on mobile so the software keyboard doesn't collapse
        setTimeout(() => {
            ui.guessInput.focus({ preventScroll: true });
        }, 100);

        // Update give up option visibility on incorrect guess
        updateGiveUpButtonVisibility();
    }
}


function getApprovedChallenges() {
    const approved = puzzles.filter(p => p.status === 'approved' && p.puzzle_number);
    approved.sort((a, b) => parseInt(a.puzzle_number) - parseInt(b.puzzle_number));
    
    // Stop at the current active challenge (todayChallenge)
    if (todayChallenge && !isPreviewMode) {
        const todayNum = parseInt(todayChallenge.puzzle_number);
        return approved.filter(p => parseInt(p.puzzle_number) <= todayNum);
    }
    return approved;
}

function navigateChallenge(direction) {
    const approved = getApprovedChallenges();
    if (approved.length === 0 || !activeChallenge) return;

    const currentIndex = approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number);
    if (currentIndex === -1) return;

    // Prevent navigation if the target direction is disabled
    if (direction === 1 && currentIndex >= approved.length - 1) return;
    if (direction === -1 && currentIndex <= 0) return;

    const newIndex = currentIndex + direction;
    if (newIndex >= 0 && newIndex < approved.length) {
        startGame(approved[newIndex]);
        history.replaceState(null, "", `?challenge=${approved[newIndex].puzzle_number}`);
    }
}

function viewPreviousChallenge() {
    const approved = getApprovedChallenges();
    if (approved.length === 0 || !activeChallenge) return;

    const currentIndex = approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number);
    if (currentIndex <= 0) return;

    const previousChallenge = approved[currentIndex - 1];
    isViewingPrevious = true;
    activeChallenge = previousChallenge;
    hintsUsed = 0;

    sendTelemetryEvent('challenge_view');
    triggerVictory();
}

function giveUpChallenge() {
    if (!activeChallenge) return;
    isViewingPrevious = true;
    triggerVictory();
}

function updateGiveUpButtonVisibility() {
    const giveUpBtn = document.getElementById('btn-give-up');
    if (!giveUpBtn || !activeChallenge) return;

    const attemptsMap = getPuzzleAttemptsMap();
    const attemptsCount = attemptsMap[activeChallenge.puzzle_number] || 0;

    if (hintsUsed === 4 && attemptsCount >= 3) {
        giveUpBtn.classList.remove('hidden');
    } else {
        giveUpBtn.classList.add('hidden');
    }
}

function updateChallengeNavButtons() {
    const approved = getApprovedChallenges();
    const prevBtn = document.getElementById('btn-prev-challenge');
    const nextBtn = document.getElementById('btn-next-challenge');
    const prevBtnVic = document.getElementById('btn-prev-challenge-victory');
    const nextBtnVic = document.getElementById('btn-next-challenge-victory');
    
    if (isItch) {
        if (prevBtn) prevBtn.style.display = 'none';
        if (nextBtn) nextBtn.style.display = 'none';
        if (prevBtnVic) prevBtnVic.style.display = 'none';
        if (nextBtnVic) nextBtnVic.style.display = 'none';
        return;
    }
    
    const disablePrev = (approved.length === 0 || !activeChallenge || approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number) <= 0);
    const disableNext = (approved.length === 0 || !activeChallenge || approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number) >= approved.length - 1);
    
    if (prevBtn) prevBtn.disabled = disablePrev;
    if (nextBtn) nextBtn.disabled = disableNext;
    if (prevBtnVic) prevBtnVic.disabled = disablePrev;
    if (nextBtnVic) {
        nextBtnVic.classList.toggle('disabled', disableNext);
        nextBtnVic.disabled = false; // Keep it enabled for hover events
    }
}

function renderStreakCalendar() {
    const gridEl = document.getElementById('streak-grid');
    if (!gridEl) return;
    gridEl.innerHTML = '';

    const solvedList = getSolvedPuzzlesList();
    const approved = getApprovedChallenges();
    
    // We want a rolling 7-day window ending at naturalTodayIndex (the latest active daily challenge)
    const endChallengeNum = naturalTodayIndex;
    const startChallengeNum = Math.max(1, endChallengeNum - 6);

    for (let i = startChallengeNum; i <= endChallengeNum; i++) {
        const paddedNum = padPuzzleNumber(i);
        const isSolved = solvedList.has(paddedNum);
        const isToday = i === endChallengeNum;

        const box = document.createElement('div');
        box.className = 'streak-day-box';
        // Display the shortened number (strip leading zeros to keep it clean)
        box.innerText = i.toString();

        if (isSolved) {
            box.classList.add('solved');
            box.title = `Challenge #${paddedNum} - Solved!`;
        } else if (isToday) {
            box.classList.add('today');
            box.title = `Challenge #${paddedNum} - Today's challenge!`;
        } else {
            box.classList.add('missed');
            box.title = `Challenge #${paddedNum} - Missed`;
            
            // Allow clicking missed historical challenges on non-itch environments to play and restore streak
            if (!isItch) {
                const challengeObj = approved.find(p => p.puzzle_number === paddedNum);
                if (challengeObj) {
                    box.style.cursor = 'pointer';
                    box.onclick = () => {
                        startGame(challengeObj);
                        history.replaceState(null, "", `?challenge=${challengeObj.puzzle_number}`);
                    };
                }
            }
        }

        gridEl.appendChild(box);
    }
}

function triggerVictory() {
    if (!isViewingPrevious && isCrazyGames && typeof window.CrazyGames !== 'undefined') {
        try {
            window.CrazyGames.SDK.game.gameplayStop();
            console.log("CrazyGames gameplayStop signaled.");
        } catch (e) {
            console.warn("CrazyGames gameplayStop failed:", e);
        }
    }
    currentLevel = 5;

    // Render victory postcard frame immediately
    ui.victoryPosterImg.src = getCorrectPosterUrl(activeChallenge.boss_poster_url);
    ui.finalBossTitle.innerText = activeChallenge.boss_pun_title;
    ui.finalBossMovie.innerText = `Real Location: ${activeChallenge.boss_original_title}`;
    
    // Set Wikipedia and Google Maps search URLs
    const cleanName = activeChallenge.boss_original_title.trim();
    const wikiSlug = cleanName.replace(/\s+/g, '_');
    if (ui.linkWikipedia) {
        ui.linkWikipedia.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(wikiSlug)}`;
    }
    if (ui.linkMaps) {
        ui.linkMaps.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanName + ' landmark')}`;
    }
    
    // Response from the Owner
    ui.finalBossPitch.innerHTML = `
        <div style="text-align: left; width: 100%;">
            <strong style="color: var(--accent-main); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">Response from the Owner:</strong>
            <em style="color: #4a5568; display: block; font-style: italic; font-family: var(--font-body); line-height: 1.45; font-size: 0.9rem; font-weight: 600;">
                "${activeChallenge.boss_pitch || 'No response.'}"
            </em>
        </div>
    `;

    // Reset 1-star reviews toggle state to collapsed
    const toggleReviewsBtn = document.getElementById('btn-toggle-reviews');
    const finalBossQuote = document.getElementById('final-boss-quote');
    if (toggleReviewsBtn && finalBossQuote) {
        finalBossQuote.classList.add('hidden');
        toggleReviewsBtn.innerText = '1-Star Reviews ▼';
    }

    const quoteEl = document.getElementById('final-boss-quote');
    if (quoteEl) {
        quoteEl.innerHTML = `
            <div style="font-family: var(--font-body); font-size: 0.9rem; line-height: 1.4; color: #ff4757; text-align: left;">
                <strong style="color: #ff4757; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">1-Star Reviews:</strong>
                <ul style="margin: 5px 0 0 15px; padding: 0; color: #ff4757; font-weight: 700; list-style-type: disc;">
                    <li style="margin-bottom: 6px;">"${activeChallenge.clue1}"</li>
                    <li style="margin-bottom: 6px;">"${activeChallenge.clue2}"</li>
                    <li style="margin-bottom: 0;">"${activeChallenge.clue3}"</li>
                </ul>
            </div>
        `;
    }

    if (ui.challengeHeaderVictory) {
        ui.challengeHeaderVictory.innerHTML = `<span class="challenge-label">Challenge</span> #<span class="level-indicator-num">${activeChallenge.puzzle_number}</span>`;
    }
    updateChallengeNavButtons();

    // Render the rolling 7-day streak calendar grid
    renderStreakCalendar();

    // Set up dynamic share score nudge text based on performance
    const nudgeEl = document.getElementById('share-nudge');
    const shareBtn = document.getElementById('btn-share-score');
    if (isViewingPrevious) {
        if (nudgeEl) nudgeEl.classList.add('hidden');
        if (shareBtn) shareBtn.classList.add('hidden');
    } else {
        if (nudgeEl) {
            nudgeEl.classList.remove('hidden');
            if (hintsUsed === 0) {
                nudgeEl.innerText = "Show off your perfect score to friends! 🏆";
            } else {
                nudgeEl.innerText = "Show off your score to friends! 🗺️";
            }
        }
        if (shareBtn) shareBtn.classList.remove('hidden');
    }

    // Set up victory lobby button dynamically
    const lobbyBtn = document.getElementById('btn-victory-lobby');
    const playRandomBtn = document.getElementById('btn-play-random');
    const allCompletedMsg = document.getElementById('all-completed-msg');
    
    const solvedList = getSolvedPuzzlesList();
    const approved = getApprovedChallenges();
    const uncompleted = approved.filter(p => !solvedList.has(p.puzzle_number));

    if (isViewingPrevious) {
        if (lobbyBtn) {
            const isToday = todayChallenge && activeChallenge && activeChallenge.puzzle_number === todayChallenge.puzzle_number;
            if (isToday && !solvedList.has(todayChallenge.puzzle_number)) {
                lobbyBtn.innerHTML = `🎯 TRY AGAIN`;
            } else {
                lobbyBtn.innerHTML = `🎯 BACK TO TODAY'S CHALLENGE`;
            }
            lobbyBtn.classList.remove('hidden');
            lobbyBtn.onclick = () => {
                startGame(todayChallenge);
                history.replaceState(null, "", `?challenge=${todayChallenge.puzzle_number}`);
            };
        }
        if (playRandomBtn) playRandomBtn.classList.add('hidden');
        if (allCompletedMsg) allCompletedMsg.classList.add('hidden');
    } else {
        if (lobbyBtn) {
            if (isItch) {
                lobbyBtn.innerHTML = `🎮 PLAY ALL & TRACK STREAK ➔`;
                lobbyBtn.classList.remove('hidden');
                lobbyBtn.onclick = () => {
                    window.open('https://iwandres.github.io/PunFiction/travelreviews/', '_blank');
                };
            } else {
                const currentIndex = approved.findIndex(p => p.puzzle_number === activeChallenge.puzzle_number);
                
                if (uncompleted.length > 0 && currentIndex !== -1 && currentIndex < approved.length - 1) {
                    const nextChallenge = approved[currentIndex + 1];
                    lobbyBtn.innerHTML = `⏭️ PLAY CHALLENGE #${nextChallenge.puzzle_number}`;
                    lobbyBtn.classList.remove('hidden');
                    lobbyBtn.onclick = () => {
                        startGame(nextChallenge);
                        history.replaceState(null, "", `?challenge=${nextChallenge.puzzle_number}`);
                    };
                } else {
                    lobbyBtn.classList.add('hidden');
                }
            }
        }

        if (playRandomBtn && allCompletedMsg) {
            if (isItch) {
                playRandomBtn.classList.add('hidden');
                allCompletedMsg.classList.add('hidden');
            } else {
                if (uncompleted.length === 0) {
                    playRandomBtn.classList.add('hidden');
                    if (todayChallenge && activeChallenge.puzzle_number === todayChallenge.puzzle_number) {
                        if (lobbyBtn) lobbyBtn.classList.add('hidden');
                        allCompletedMsg.classList.remove('hidden');
                    } else {
                        allCompletedMsg.classList.add('hidden');
                        if (lobbyBtn && todayChallenge) {
                            lobbyBtn.innerHTML = `🎯 PLAY TODAY'S CHALLENGE`;
                            lobbyBtn.classList.remove('hidden');
                            lobbyBtn.onclick = () => {
                                startGame(todayChallenge);
                                history.replaceState(null, "", `?challenge=${todayChallenge.puzzle_number}`);
                            };
                        }
                    }
                } else {
                    allCompletedMsg.classList.add('hidden');
                    
                    // Select a random uncompleted challenge
                    const randomIndex = Math.floor(Math.random() * uncompleted.length);
                    const randomChallenge = uncompleted[randomIndex];
                    
                    playRandomBtn.classList.remove('hidden');
                    playRandomBtn.onclick = () => {
                        startGame(randomChallenge);
                        history.replaceState(null, "", `?challenge=${randomChallenge.puzzle_number}`);
                    };
                }
            }
        }
    }

    // Render solved status badge above poster
    const solvedStatus = document.getElementById('victory-solved-status');
    if (solvedStatus) {
        if (isViewingPrevious) {
            solvedStatus.classList.add('hidden');
        } else {
            const solvedList = getSolvedPuzzlesList();
            if (solvedList.has(activeChallenge.puzzle_number)) {
                const solvedHints = getSolvedHintsMap();
                const used = solvedHints[activeChallenge.puzzle_number] !== undefined ? solvedHints[activeChallenge.puzzle_number] : hintsUsed;
                
                const attemptsMap = getPuzzleAttemptsMap();
                const attemptsCount = attemptsMap[activeChallenge.puzzle_number] || 1;
                
                const hintText = used === 0 ? "No Hints" : `${used} Hint${used > 1 ? 's' : ''}`;
                const attemptText = `${attemptsCount} Attempt${attemptsCount > 1 ? 's' : ''}`;
                
                solvedStatus.innerText = `Solved! ${hintText} • ${attemptText}`;
                solvedStatus.classList.remove('hidden');
            } else {
                solvedStatus.classList.add('hidden');
            }
        }
    }

    // Switch screen to Victory instantly!
    if (!isViewingPrevious && isCrazyGames && typeof window.CrazyGames !== 'undefined') {
        console.log("Requesting CrazyGames midgame ad on victory...");
        window.CrazyGames.SDK.ad.requestAd('midgame', {
            adStarted: () => {
                console.log("CrazyGames midgame ad started");
            },
            adError: (error) => {
                console.error("CrazyGames midgame ad error:", error);
                switchScreen('victory');
                loadAndRenderGlobalStats(activeChallenge.puzzle_number);
            },
            adFinished: () => {
                console.log("CrazyGames midgame ad finished");
                switchScreen('victory');
                loadAndRenderGlobalStats(activeChallenge.puzzle_number);
            }
        });
    } else {
        switchScreen('victory');
        loadAndRenderGlobalStats(activeChallenge.puzzle_number);
    }
}

async function loadAndRenderGlobalStats(puzzleNum) {
    const solveRateBadge = document.getElementById('solve-rate-badge');
    if (solveRateBadge) {
        solveRateBadge.innerText = "⚡ RETRIEVING LIVE TRAVEL METRICS...";
    }
    
    const funnelContainer = document.querySelector('.funnel-container');
    if (funnelContainer) {
        funnelContainer.classList.add('loading');
    }
    
    // Fetch combined telemetry stats
    await fetchAllTelemetryStats();
    
    if (funnelContainer) {
        funnelContainer.classList.remove('loading');
    }
    
    const originalStats = getPuzzleTelemetryStats(puzzleNum);
    // Clone stats object to avoid modifying cached reference directly
    const stats = { ...originalStats };
    
    // Ensure the current user's solve is accounted for if they solved it (either in this session or in the past)
    const solvedList = getSolvedPuzzlesList();
    const solvedHints = getSolvedHintsMap();
    const isPuzzleSolved = solvedList.has(puzzleNum);
    
    if (stats) {
        const wasSolvedThisSession = !isViewingPrevious;
        const wasSolvedPast = isViewingPrevious && isPuzzleSolved;
        
        if (wasSolvedThisSession || wasSolvedPast) {
            stats.start = (stats.start || 0) + 1;
            
            let usedHints = hintsUsed;
            if (wasSolvedPast) {
                usedHints = solvedHints[puzzleNum] !== undefined ? solvedHints[puzzleNum] : 0;
            }
            
            const clampedHints = Math.max(0, Math.min(4, parseInt(usedHints) || 0));
            stats[`solve_${clampedHints}`] = (stats[`solve_${clampedHints}`] || 0) + 1;
        }
    }
    
    // Calculate percentages
    let totalStarts = stats.start || 1;
    let totalSolves = (stats.solve_0 || 0) + (stats.solve_1 || 0) + (stats.solve_2 || 0) + (stats.solve_3 || 0) + (stats.solve_4 || 0);
    if (totalStarts < totalSolves) totalStarts = totalSolves;
    
    const solveRate = Math.round((totalSolves / totalStarts) * 100);
    
    let pct0 = 0, pct1 = 0, pct2 = 0, pct3 = 0, pct4 = 0;
    if (totalSolves > 0) {
        pct0 = Math.round((stats.solve_0 / totalSolves) * 100);
        pct1 = Math.round((stats.solve_1 / totalSolves) * 100);
        pct2 = Math.round((stats.solve_2 / totalSolves) * 100);
        pct3 = Math.round((stats.solve_3 / totalSolves) * 100);
        pct4 = Math.round((stats.solve_4 / totalSolves) * 100);
        
        const sum = pct0 + pct1 + pct2 + pct3 + pct4;
        if (sum !== 100 && sum > 0) {
            const diff = 100 - sum;
            const maxVal = Math.max(pct0, pct1, pct2, pct3, pct4);
            if (pct0 === maxVal) pct0 += diff;
            else if (pct1 === maxVal) pct1 += diff;
            else if (pct2 === maxVal) pct2 += diff;
            else if (pct3 === maxVal) pct3 += diff;
            else pct4 += diff;
        }
    } else {
        pct0 = 0; pct1 = 0; pct2 = 0; pct3 = 0; pct4 = 0;
    }
    
    // Render Stats
    if (solveRateBadge) {
        solveRateBadge.innerText = `${solveRate}% OF PLAYERS CRACKED THIS CHALLENGE!`;
    }
    
    const fill0 = document.getElementById('funnel-fill-0');
    const fill1 = document.getElementById('funnel-fill-1');
    const fill2 = document.getElementById('funnel-fill-2');
    const fill3 = document.getElementById('funnel-fill-3');
    const fill4 = document.getElementById('funnel-fill-4');
    
    const pct0Label = document.getElementById('funnel-pct-0');
    const pct1Label = document.getElementById('funnel-pct-1');
    const pct2Label = document.getElementById('funnel-pct-2');
    const pct3Label = document.getElementById('funnel-pct-3');
    const pct4Label = document.getElementById('funnel-pct-4');
    
    if (fill0) fill0.style.width = '0%';
    if (fill1) fill1.style.width = '0%';
    if (fill2) fill2.style.width = '0%';
    if (fill3) fill3.style.width = '0%';
    if (fill4) fill4.style.width = '0%';
    
    if (pct0Label) pct0Label.innerText = '0%';
    if (pct1Label) pct1Label.innerText = '0%';
    if (pct2Label) pct2Label.innerText = '0%';
    if (pct3Label) pct3Label.innerText = '0%';
    if (pct4Label) pct4Label.innerText = '0%';
    
    setTimeout(() => {
        if (fill0) fill0.style.width = `${pct0}%`;
        if (fill1) fill1.style.width = `${pct1}%`;
        if (fill2) fill2.style.width = `${pct2}%`;
        if (fill3) fill3.style.width = `${pct3}%`;
        if (fill4) fill4.style.width = `${pct4}%`;
        
        if (pct0Label) pct0Label.innerText = `${pct0}%`;
        if (pct1Label) pct1Label.innerText = `${pct1}%`;
        if (pct2Label) pct2Label.innerText = `${pct2}%`;
        if (pct3Label) pct3Label.innerText = `${pct3}%`;
        if (pct4Label) pct4Label.innerText = `${pct4}%`;
    }, 200);
}

function getMaskedParodyTitle(title) {
    if (!title) return "";
    const words = title.split(/\s+/);
    const maskedWords = words.map(word => {
        if (!word) return "";
        const firstAlphanumericIndex = word.search(/[a-zA-Z0-9]/);
        if (firstAlphanumericIndex === -1) {
            return word;
        }
        const prefix = word.substring(0, firstAlphanumericIndex);
        const letter = word.charAt(firstAlphanumericIndex);
        const suffix = word.substring(firstAlphanumericIndex + 1);
        const maskedSuffix = suffix.replace(/[a-zA-Z0-9]/g, '_');
        return prefix + letter + maskedSuffix;
    });

    if (maskedWords.length > 2) {
        let truncated = maskedWords.slice(0, 2).join(" ");
        // Strip trailing non-alphanumeric/non-underscore characters from the end of the truncated string
        truncated = truncated.replace(/[^a-zA-Z0-9_]+$/, '');
        return truncated + "...";
    }
    return maskedWords.join(" ");
}

// Share score streak via clipboard copy
function shareSolvedScore() {
    // Add hint count to the share text
    const hintText = hintsUsed === 0 ? "No hints used! Perfect score! 🌟" : `${hintsUsed}/4 hints used 💡`;

    const copyText = `PunFiction Daily Challenge #${activeChallenge.puzzle_number} 🗺️\n` + 
                     `Parody Solved: "${getMaskedParodyTitle(activeChallenge.boss_pun_title)}"\n` +
                     `Stats: ${hintText}\n` +
                     `Play daily challenge at: https://iwandres.github.io/PunFiction/travelreviews/`;

    navigator.clipboard.writeText(copyText).then(() => {
        showToast("📢 Streak Score copied to clipboard!");
    }).catch(err => {
        console.error("Failed copying streak text: ", err);
    });
}

// ================= DYNAMIC UI EFFECTS =================

function shakeInput() {
    if (ui.guessSlotsContainer) {
        ui.guessSlotsContainer.style.animation = 'none';
        ui.guessSlotsContainer.offsetHeight; /* trigger reflow */
        ui.guessSlotsContainer.style.animation = 'shake 0.3s ease-in-out';
    }
}

// Inject Keyframe animations dynamically to keep client lightweight
const styleSheet = document.createElement("style");
styleSheet.innerText = `
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-8px); }
    75% { transform: translateX(8px); }
}
.toast-container {
    position: fixed;
    bottom: 25px;
    left: 50%;
    transform: translateX(-50%);
    background: #5f27cd;
    color: #ffffff;
    padding: 10px 20px;
    border: 3px solid #2d3436;
    box-shadow: 4px 4px 0px #2d3436;
    border-radius: 8px;
    font-weight: 900;
    font-size: 13px;
    z-index: 9999;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}
.hint-container {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    max-height: 100px;
    opacity: 1;
    overflow: hidden;
}
.hint-container.collapsed {
    max-height: 0 !important;
    min-height: 0 !important;
    margin-bottom: 0 !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    opacity: 0 !important;
}
.rhyme-word {
    transition: color 0.3s ease, font-weight 0.3s ease;
    display: inline-block;
}
.rhyme-word.revealed {
    color: var(--text-secondary) !important;
    font-weight: 800;
}
.hint-particle {
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: radial-gradient(circle, #ff90ec 0%, #8c52ff 70%, #5f27cd 100%);
    box-shadow: 0 0 10px #8c52ff;
    pointer-events: none;
    z-index: 10001;
    transform: translate(-50%, -50%);
}
.hint-sparkle {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    pointer-events: none;
    z-index: 10001;
    transform: translate(-50%, -50%);
}
.comet-head {
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 0 15px #a855f7, 0 0 30px #5f27cd;
    border: 2px solid #5f27cd;
    pointer-events: none;
    z-index: 10002;
    transform: translate(-50%, -50%);
}
`;
document.head.appendChild(styleSheet);

function showToast(message, isError = false) {
    const toast = document.createElement("div");
    toast.className = "toast-container";
    if (isError) {
        toast.style.background = "#ff4757";
    }
    toast.innerText = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "none";
        toast.style.transition = "opacity 0.3s";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ================= GRACEFUL ARC ANIMATION FOR HINT 1 =================

function animateHintArc(startX, startY, endX, endY, callback) {
    // Create temporary SVG element covering document size
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const docHeight = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    svg.setAttribute("style", `position: absolute; top: 0; left: 0; width: 100%; height: ${docHeight}px; pointer-events: none; z-index: 10000;`);
    
    // Calculate control point for standard quadratic Bezier curve arcing upwards/outwards
    const dx = endX - startX;
    const dy = endY - startY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    const perpX = -dy / dist;
    const perpY = dx / dist;
    const offset = Math.min(150, Math.max(60, dist * 0.35));
    const dir = perpY > 0 ? -1 : 1;
    
    const controlX = (startX + endX) / 2 + perpX * offset * dir;
    const controlY = (startY + endY) / 2 + perpY * offset * dir;
    
    // Create trajectory path
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const dStr = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
    path.setAttribute("d", dStr);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "rgba(95, 39, 205, 0.2)");
    path.setAttribute("stroke-width", "3");
    path.setAttribute("stroke-dasharray", "6,6");
    svg.appendChild(path);
    
    document.body.appendChild(svg);
    
    const pathLength = path.getTotalLength();
    
    // Create comet head element
    const comet = document.createElement("div");
    comet.className = "comet-head";
    document.body.appendChild(comet);
    
    const duration = 900; // ms
    const startTime = performance.now();
    let lastParticleTime = 0;
    
    function easeOutCubic(x) {
        return 1 - Math.pow(1 - x, 3);
    }
    
    function update(time) {
        const elapsed = time - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = easeOutCubic(progress);
        
        const currentLength = easeProgress * pathLength;
        const point = path.getPointAtLength(currentLength);
        
        comet.style.left = `${point.x}px`;
        comet.style.top = `${point.y}px`;
        
        if (time - lastParticleTime > 15 && progress < 1) {
            spawnTrailParticle(point.x, point.y);
            lastParticleTime = time;
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            comet.remove();
            svg.remove();
            spawnExplosion(endX, endY);
            if (callback) callback();
        }
    }
    
    requestAnimationFrame(update);
}

function spawnTrailParticle(x, y) {
    const p = document.createElement("div");
    p.className = "hint-particle";
    p.style.left = `${x}px`;
    p.style.top = `${y}px`;
    
    const sz = 6 + Math.random() * 6;
    p.style.width = `${sz}px`;
    p.style.height = `${sz}px`;
    
    document.body.appendChild(p);
    
    const duration = 400 + Math.random() * 200;
    p.animate([
        { transform: 'translate(-50%, -50%) scale(1)', opacity: 0.8 },
        { transform: 'translate(-50%, -50%) scale(0.1)', opacity: 0 }
    ], {
        duration: duration,
        easing: 'ease-out'
    });
    
    setTimeout(() => p.remove(), duration);
}

function spawnExplosion(x, y) {
    const numSparkles = 16;
    for (let i = 0; i < numSparkles; i++) {
        const s = document.createElement("div");
        s.className = "hint-sparkle";
        s.style.left = `${x}px`;
        s.style.top = `${y}px`;
        
        const color = i % 2 === 0 ? "#a855f7" : "#ffde59";
        s.style.background = color;
        s.style.boxShadow = `0 0 6px ${color}`;
        
        document.body.appendChild(s);
        
        const angle = Math.random() * Math.PI * 2;
        const speed = 40 + Math.random() * 80;
        const tx = Math.cos(angle) * speed;
        const ty = Math.sin(angle) * speed;
        
        const duration = 600 + Math.random() * 400;
        
        s.animate([
            { transform: 'translate(-50%, -50%) scale(1.5)', opacity: 1 },
            { transform: `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px)) scale(0.1)`, opacity: 0 }
        ], {
            duration: duration,
            easing: 'cubic-bezier(0.1, 0.8, 0.3, 1)'
        });
        
        setTimeout(() => s.remove(), duration);
    }
}

// ================= TELEMETRY UTILITY METHODS =================

function getDeterministicMockMetrics(puzzleNum) {
    const num = parseInt(puzzleNum) || 1;
    const pseudoSeed = (num * 9301 + 49297) % 233280;
    const seedFactor = pseudoSeed / 233280;
    
    const totalStarts = Math.floor(250 + seedFactor * 500); // 250 to 750
    const solveRatePct = Math.floor(55 + seedFactor * 35); // 55% to 90%
    const totalSolves = Math.round(totalStarts * (solveRatePct / 100));
    
    // Create highly distinct distributions based on puzzle number to avoid looking like "overall averages"
    const p1 = 0.20 + ((num * 17) % 25) / 100; // 20% to 45%
    const p2 = 0.18 + ((num * 23) % 20) / 100; // 18% to 38%
    const p3 = 0.10 + ((num * 13) % 15) / 100; // 10% to 25%
    const p4 = 0.08 + ((num * 7) % 10) / 100;  // 8% to 18%
    const p5 = Math.max(0.02, 1.0 - p1 - p2 - p3 - p4);
    
    const sumP = p1 + p2 + p3 + p4 + p5;
    const solve_0 = Math.round(totalSolves * (p1 / sumP));
    const solve_1 = Math.round(totalSolves * (p2 / sumP));
    const solve_2 = Math.round(totalSolves * (p3 / sumP));
    const solve_3 = Math.round(totalSolves * (p4 / sumP));
    const solve_4 = Math.max(0, totalSolves - solve_0 - solve_1 - solve_2 - solve_3);
    
    // Deterministic mock attempts-to-solve distribution
    const sa1 = Math.round(totalSolves * 0.35); // 35% in 1 attempt
    const sa2 = Math.round(totalSolves * 0.30); // 30% in 2 attempts
    const sa3 = Math.round(totalSolves * 0.18); // 18% in 3 attempts
    const sa4 = Math.round(totalSolves * 0.10); // 10% in 4 attempts
    const sa5 = Math.max(0, totalSolves - sa1 - sa2 - sa3 - sa4); // remaining in 5+ attempts
    
    return {
        start: totalStarts,
        attempts: totalSolves * 3 + (totalStarts - totalSolves) * 2,
        solve_0: solve_0,
        solve_1: solve_1,
        solve_2: solve_2,
        solve_3: solve_3,
        solve_4: solve_4,
        solve_att_1: sa1,
        solve_att_2: sa2,
        solve_att_3: sa3,
        solve_att_4: sa4,
        solve_att_5: sa5
    };
}

function triggerStartTelemetry() {
    if (activeChallenge && activeChallenge.puzzle_number) {
        savePuzzleAttempted(activeChallenge.puzzle_number);
    }
    if (telemetryStartSent) return;
    telemetryStartSent = true;
    sendTelemetryEvent('start');
}

async function sendTelemetryEvent(event, hints = 0) {
    const puzzleNum = activeChallenge ? activeChallenge.puzzle_number : null;
    if (!puzzleNum) return;
    
    let attemptsCount = 1;
    if (event === 'solve') {
        const attemptsMap = getPuzzleAttemptsMap();
        attemptsCount = attemptsMap[puzzleNum] || 1;
    }
    
    const payload = {
        event: event,
        puzzle_number: puzzleNum,
        hints_used: hints,
        attempts: attemptsCount
    };
    
    try {
        const telemetryUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? '/api/records'
            : `${BACKEND_API_URL}/api/travelreviews/records`;
        
        await fetch(telemetryUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.log("Telemetry post failed.", e);
    }
}

// ================= REWARDED AD LOGIC (GOOGLE PUBLISHER TAG) =================

function requestNextRewardedAd() {
    if (isCrazyGames) return; // Skip Google GPT ads on CrazyGames
    if (typeof googletag === 'undefined') {
        console.warn("googletag is not defined. Offline fallback active.");
        return;
    }
    
    googletag.cmd.push(() => {
        if (rewardedSlot) {
            console.log("Ad slot already exists and is preloading.");
            return;
        }
        
        console.log("Requesting next GPT rewarded slot with production unit...");
        rewardedSlot = googletag.defineOutOfPageSlot(
            '/23355087107/PunFiction_Web_Rewarded',
            googletag.enums.OutOfPageFormat.REWARDED
        );
        
        if (rewardedSlot) {
            rewardedSlot.addService(googletag.pubads());
            googletag.display(rewardedSlot);
            googletag.pubads().refresh([rewardedSlot]);
        } else {
            console.warn("Failed to create Out-Of-Page rewarded slot.");
        }
    });
}

// ================= STATS & LEVEL SELECT CONTROLLER =================

async function fetchAllTelemetryStats(force = false) {
    if (allTelemetry && !force) return allTelemetry;
    
    let liveData = {};
    let staticData = {};
    let fetchSuccess = false;
    
    try {
        const telemetryUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? '/api/records'
            : `${BACKEND_API_URL}/api/travelreviews/records`;
            
        const response = await fetchWithTimeout(telemetryUrl, { timeout: 3500 });
        if (response.ok) {
            const data = await response.json();
            if (data && typeof data === 'object' && !data.hasOwnProperty('start')) {
                liveData = data;
                fetchSuccess = true;
                console.log("Live telemetry fetched successfully for merging.");
            }
        }
    } catch (e) {
        console.log("Failed to fetch live telemetry for merging, using empty object.", e);
    }
    
    try {
        const staticUrl = `${GITHUB_REPO_URL}/travelreviews_records.json?t=${Date.now()}`;
        const response = await fetchWithTimeout(staticUrl, { timeout: 3500 });
        if (response.ok) {
            const data = await response.json();
            if (data && typeof data === 'object') {
                staticData = data;
                fetchSuccess = true;
                console.log("Static telemetry fetched successfully for merging.");
            }
        }
    } catch (staticE) {
        console.log("Static telemetry fetch for merging failed.", staticE);
    }
    
    telemetryFetchSucceeded = fetchSuccess;
    
    // Merge live and static data (with auto-detect to prevent double-counting)
    allTelemetry = {};
    const allKeys = new Set([...Object.keys(liveData), ...Object.keys(staticData)]);
    allKeys.forEach(key => {
        const live = liveData[key] || {};
        const stat = staticData[key] || {};
        
        const liveStart = parseInt(live.start) || 0;
        const statStart = parseInt(stat.start) || 0;
        
        if (liveStart >= statStart) {
            // Live database has more or equal starts (contains full history). Use live to prevent double-counting.
            allTelemetry[key] = {
                start: liveStart,
                attempts: parseInt(live.attempts) || 0,
                solve_0: parseInt(live.solve_0) || 0,
                solve_1: parseInt(live.solve_1) || 0,
                solve_2: parseInt(live.solve_2) || 0,
                solve_3: parseInt(live.solve_3) || 0,
                solve_4: parseInt(live.solve_4) || 0,
                solve_att_1: parseInt(live.solve_att_1) || 0,
                solve_att_2: parseInt(live.solve_att_2) || 0,
                solve_att_3: parseInt(live.solve_att_3) || 0,
                solve_att_4: parseInt(live.solve_att_4) || 0,
                solve_att_5: parseInt(live.solve_att_5) || 0
            };
        } else {
            // Live database is smaller (indicates a database reset). Sum them to recover history.
            allTelemetry[key] = {
                start: liveStart + statStart,
                attempts: (parseInt(live.attempts) || 0) + (parseInt(stat.attempts) || 0),
                solve_0: (parseInt(live.solve_0) || 0) + (parseInt(stat.solve_0) || 0),
                solve_1: (parseInt(live.solve_1) || 0) + (parseInt(stat.solve_1) || 0),
                solve_2: (parseInt(live.solve_2) || 0) + (parseInt(stat.solve_2) || 0),
                solve_3: (parseInt(live.solve_3) || 0) + (parseInt(stat.solve_3) || 0),
                solve_4: (parseInt(live.solve_4) || 0) + (parseInt(stat.solve_4) || 0),
                solve_att_1: (parseInt(live.solve_att_1) || 0) + (parseInt(stat.solve_att_1) || 0),
                solve_att_2: (parseInt(live.solve_att_2) || 0) + (parseInt(stat.solve_att_2) || 0),
                solve_att_3: (parseInt(live.solve_att_3) || 0) + (parseInt(stat.solve_att_3) || 0),
                solve_att_4: (parseInt(live.solve_att_4) || 0) + (parseInt(stat.solve_att_4) || 0),
                solve_att_5: (parseInt(live.solve_att_5) || 0) + (parseInt(stat.solve_att_5) || 0)
            };
        }
    });
    
    return allTelemetry;
}

function getPuzzleTelemetryStats(puzzleNum) {
    if (allTelemetry && allTelemetry[puzzleNum]) {
        if (allTelemetry[puzzleNum].start > 0 || telemetryFetchSucceeded) {
            return allTelemetry[puzzleNum];
        }
    }
    
    if (telemetryFetchSucceeded) {
        return {
            start: 0,
            attempts: 0,
            solve_0: 0,
            solve_1: 0,
            solve_2: 0,
            solve_3: 0,
            solve_4: 0,
            solve_att_1: 0,
            solve_att_2: 0,
            solve_att_3: 0,
            solve_att_4: 0,
            solve_att_5: 0
        };
    }
    
    return getDeterministicMockMetrics(puzzleNum);
}

function getChallengeDifficulty(challenge, stats) {
    const starts = parseInt(stats.start) || 0;
    const s0 = parseInt(stats.solve_0) || 0;
    const s1 = parseInt(stats.solve_1) || 0;
    const s2 = parseInt(stats.solve_2) || 0;
    const s3 = parseInt(stats.solve_3) || 0;
    const s4 = parseInt(stats.solve_4) || 0;
    const totalSolves = s0 + s1 + s2 + s3 + s4;
    
    if (starts > 10) {
        const solveRate = (totalSolves / starts) * 100;
        if (solveRate >= 85) return 'Easy';
        if (solveRate >= 68) return 'Medium';
        return 'Hard';
    } else {
        const tier = parseInt(challenge.difficulty_tier) || 2;
        if (tier === 1) return 'Easy';
        if (tier === 3) return 'Hard';
        return 'Medium';
    }
}

function abbreviateNumber(num) {
    if (num === null || num === undefined) return '0';
    if (num < 1000) return num.toLocaleString();
    if (num < 1000000) {
        const value = num / 1000;
        return (value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)) + 'K';
    }
    const value = num / 1000000;
    return (value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)) + 'M';
}

async function openStatsSelectModal() {
    updateWorldMapBadges();
    // 1. Show loading indicator states
    document.getElementById('agg-total-starts').innerText = '...';
    document.getElementById('agg-total-solves').innerText = '...';
    document.getElementById('agg-solve-rate').innerText = '...';
    
    for (let i = 0; i <= 4; i++) {
        const fillBar = document.getElementById(`agg-funnel-fill-${i}`);
        const pctLabel = document.getElementById(`agg-funnel-pct-${i}`);
        if (fillBar) fillBar.style.width = '0%';
        if (pctLabel) pctLabel.innerText = '0%';
    }
    
    const challengesList = document.getElementById('challenges-list');
    if (challengesList) {
        challengesList.innerHTML = '<div style="text-align: center; padding: 20px; font-weight: 800; color: var(--text-secondary);">Loading challenges...</div>';
    }

    // 2. Fetch stats
    const statsData = await fetchAllTelemetryStats(true);
    
    // 3. Aggregate stats
    const approved = getApprovedChallenges();
    let totalStarts = 0;
    let totalSolves = 0;
    const hintSolves = [0, 0, 0, 0, 0];
    
    approved.forEach(c => {
        const stats = getPuzzleTelemetryStats(c.puzzle_number);
        const starts = parseInt(stats.start) || 0;
        const s0 = parseInt(stats.solve_0) || 0;
        const s1 = parseInt(stats.solve_1) || 0;
        const s2 = parseInt(stats.solve_2) || 0;
        const s3 = parseInt(stats.solve_3) || 0;
        const s4 = parseInt(stats.solve_4) || 0;
        
        totalStarts += starts;
        totalSolves += (s0 + s1 + s2 + s3 + s4);
        hintSolves[0] += s0;
        hintSolves[1] += s1;
        hintSolves[2] += s2;
        hintSolves[3] += s3;
        hintSolves[4] += s4;
    });
    
    const solveRate = totalStarts > 0 ? ((totalSolves / totalStarts) * 100).toFixed(1) : '0.0';
    
    document.getElementById('agg-total-starts').innerText = abbreviateNumber(totalStarts);
    document.getElementById('agg-total-solves').innerText = abbreviateNumber(totalSolves);
    document.getElementById('agg-solve-rate').innerText = `${solveRate}%`;
    
    for (let i = 0; i <= 4; i++) {
        const count = hintSolves[i];
        const pct = totalSolves > 0 ? Math.round((count / totalSolves) * 100) : 0;
        const fillBar = document.getElementById(`agg-funnel-fill-${i}`);
        const pctLabel = document.getElementById(`agg-funnel-pct-${i}`);
        if (fillBar) fillBar.style.width = `${pct}%`;
        if (pctLabel) pctLabel.innerText = `${pct}%`;
    }
    
    // 4. Populate list of challenges
    if (challengesList) {
        if (isItch) {
            const titleEl = document.querySelector('.challenges-section-title');
            if (titleEl) titleEl.style.display = 'none';
            challengesList.innerHTML = `
                <div style="text-align: center; padding: 25px; background: var(--bg-color); border: 2px solid var(--border-color); border-radius: 8px; box-shadow: 4px 4px 0px var(--border-color); margin-top: 15px;">
                    <p style="margin-top: 0; font-size: 1.2rem; color: var(--accent); font-weight: 800; font-family: 'Bangers', cursive; letter-spacing: 1px;">Want to play more levels?</p>
                    <p style="font-size: 0.95rem; line-height: 1.5; color: var(--text-color); margin-bottom: 20px;">
                        The itch.io edition only displays today's puzzle. Visit the official portal to play all historical challenges, view leaderboards, and track your daily streak!
                    </p>
                    <a href="https://iwandres.github.io/PunFiction/travelreviews/" target="_blank" class="btn primary-btn" style="display: inline-block; font-size: 1.1rem; padding: 10px 20px; text-decoration: none; box-shadow: 2px 2px 0px var(--border-color); color: var(--border-color); font-weight: bold;">Play All Challenges ➔</a>
                </div>
            `;
            return;
        }
        challengesList.innerHTML = '';
        const solvedList = getSolvedPuzzlesList();
        const attemptedList = getAttemptedPuzzles();
        
        approved.forEach(c => {
            const stats = getPuzzleTelemetryStats(c.puzzle_number);
            const difficulty = getChallengeDifficulty(c, stats);
            
            const row = document.createElement('div');
            row.className = 'challenge-select-row';
            
            const isActive = activeChallenge && activeChallenge.puzzle_number === c.puzzle_number;
            if (isActive) {
                row.style.borderColor = '#5f27cd';
                row.style.background = '#f1eafd';
            }
            
            const displayNum = c.puzzle_number;
            const chalQuote = c.review_title ? `"${c.review_title}"` : '"Review Title Missing"';
            
            let statusBadgeHtml = '';
            if (solvedList.has(c.puzzle_number)) {
                statusBadgeHtml = `<span class="completion-badge solved">Solved</span>`;
            } else if (attemptedList.has(c.puzzle_number)) {
                statusBadgeHtml = `<span class="completion-badge attempted">Attempted</span>`;
            } else {
                statusBadgeHtml = `<span class="completion-badge unplayed">Unplayed</span>`;
            }
            
            row.innerHTML = `
                <div class="challenge-select-info">
                    <span class="challenge-select-num">Challenge #<span class="challenge-select-num-val">${displayNum}</span></span>
                    <span class="challenge-select-name">${chalQuote}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="difficulty-badge ${difficulty.toLowerCase()}">${difficulty}</span>
                    ${statusBadgeHtml}
                </div>
            `;
            
            row.onclick = () => {
                startGame(c);
                history.replaceState(null, "", `?challenge=${c.puzzle_number}`);
                const statsSelectModal = document.getElementById('stats-select-modal');
                if (statsSelectModal) {
                    statsSelectModal.classList.remove('active');
                }
            };
            
            challengesList.appendChild(row);
        });
    }
}

function initStreakTooltip() {
    // Only initialize hover tooltip on desktop devices with pointer support (prevents mobile touch issues)
    if (!window.matchMedia('(hover: hover)').matches) return;

    const tooltip = document.createElement('div');
    tooltip.id = 'streak-tooltip';
    tooltip.className = 'streak-tooltip hidden';
    
    const title = document.createElement('h4');
    title.className = 'streak-tooltip-title';
    title.innerText = '🔥 STREAK COUNTER';
    tooltip.appendChild(title);
    
    const grid = document.createElement('div');
    grid.className = 'streak-grid';
    grid.id = 'streak-tooltip-grid';
    tooltip.appendChild(grid);
    
    document.body.appendChild(tooltip);

    const buttons = document.querySelectorAll('.settings-btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            const solvedList = getSolvedPuzzlesList();
            if (solvedList.size === 0) return; // Only show tooltip for returning players with solved puzzles
            
            renderTooltipGrid();
            
            const rect = btn.getBoundingClientRect();
            const scrollX = window.scrollX || window.pageXOffset;
            const scrollY = window.scrollY || window.pageYOffset;
            
            // Center the tooltip horizontally relative to the button
            tooltip.style.left = `${rect.left + scrollX + (rect.width / 2) - 130}px`; // 130px is half of tooltip width (260px)
            tooltip.style.top = `${rect.bottom + scrollY + 8}px`;
            
            tooltip.classList.remove('hidden');
            tooltip.offsetHeight; // force reflow for opacity transition
            tooltip.classList.add('active');
        });
        
        btn.addEventListener('mouseleave', () => {
            tooltip.classList.remove('active');
            tooltip.classList.add('hidden');
        });
    });
}

function renderTooltipGrid() {
    const gridEl = document.getElementById('streak-tooltip-grid');
    if (!gridEl) return;
    gridEl.innerHTML = '';

    const solvedList = getSolvedPuzzlesList();
    
    const endChallengeNum = naturalTodayIndex;
    const startChallengeNum = Math.max(1, endChallengeNum - 6);

    for (let i = startChallengeNum; i <= endChallengeNum; i++) {
        const paddedNum = padPuzzleNumber(i);
        const isSolved = solvedList.has(paddedNum);
        const isToday = i === endChallengeNum;

        const box = document.createElement('div');
        box.className = 'streak-day-box';
        box.innerText = i.toString();

        if (isSolved) {
            box.classList.add('solved');
        } else if (isToday) {
            box.classList.add('today');
        } else {
            box.classList.add('missed');
        }

        gridEl.appendChild(box);
    }
}

function renderProfileStreakCalendar() {
    const gridEl = document.getElementById('profile-streak-grid');
    if (!gridEl) return;
    gridEl.innerHTML = '';

    const solvedList = getSolvedPuzzlesList();
    const approved = getApprovedChallenges();
    
    const endChallengeNum = naturalTodayIndex;
    const startChallengeNum = Math.max(1, endChallengeNum - 6);

    for (let i = startChallengeNum; i <= endChallengeNum; i++) {
        const paddedNum = padPuzzleNumber(i);
        const isSolved = solvedList.has(paddedNum);
        const isToday = i === endChallengeNum;

        const box = document.createElement('div');
        box.className = 'streak-day-box';
        box.innerText = i.toString();

        if (isSolved) {
            box.classList.add('solved');
            box.title = `Challenge #${paddedNum} - Solved!`;
        } else if (isToday) {
            box.classList.add('today');
            box.title = `Challenge #${paddedNum} - Today's challenge!`;
        } else {
            box.classList.add('missed');
            box.title = `Challenge #${paddedNum} - Missed`;
            
            // Allow clicking missed historical challenges to play and restore streak
            if (!isItch) {
                const challengeObj = approved.find(p => p.puzzle_number === paddedNum);
                if (challengeObj) {
                    box.style.cursor = 'pointer';
                    box.onclick = () => {
                        startGame(challengeObj);
                        history.replaceState(null, "", `?challenge=${challengeObj.puzzle_number}`);
                        const settingsModal = document.getElementById('settings-modal');
                        if (settingsModal) settingsModal.classList.remove('active');
                    };
                }
            }
        }

        gridEl.appendChild(box);
    }
}

function initNextButtonVictoryTooltip() {
    // Only initialize hover tooltip on desktop devices with pointer support
    if (!window.matchMedia('(hover: hover)').matches) return;

    const tooltip = document.createElement('div');
    tooltip.id = 'next-victory-tooltip';
    tooltip.className = 'next-victory-tooltip hidden';
    tooltip.innerText = 'Congratulations, come back tomorrow for a new puzzle';
    document.body.appendChild(tooltip);

    const nextBtnVic = document.getElementById('btn-next-challenge-victory');
    if (nextBtnVic) {
        nextBtnVic.addEventListener('mouseenter', () => {
            // Show only if the button is disabled (has "disabled" class) and we are on today's challenge
            const isTodayChallenge = todayChallenge && activeChallenge && activeChallenge.puzzle_number === todayChallenge.puzzle_number;
            const isBtnDisabled = nextBtnVic.classList.contains('disabled');
            const victoryScreen = document.getElementById('victory-screen');
            const isVictoryScreenActive = victoryScreen && victoryScreen.classList.contains('active');

            if (isTodayChallenge && isBtnDisabled && isVictoryScreenActive) {
                const rect = nextBtnVic.getBoundingClientRect();
                const scrollX = window.scrollX || window.pageXOffset;
                const scrollY = window.scrollY || window.pageYOffset;
                
                // Position tooltip above the button
                tooltip.classList.remove('hidden');
                
                // Center the tooltip horizontally
                tooltip.style.left = `${rect.left + scrollX + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
                tooltip.style.top = `${rect.top + scrollY - tooltip.offsetHeight - 8}px`;
            }
        });

        nextBtnVic.addEventListener('mouseleave', () => {
            tooltip.classList.add('hidden');
        });
    }
}

// Update the daily solve streak badge inside the profile settings icon
function updateHeaderStreak() {
    updateWorldMapBadges();
    try {
        const solvedList = getSolvedPuzzlesList();
        
        const profileIcon = document.getElementById('settings-profile-icon');
        const profileIconVic = document.getElementById('settings-profile-icon-victory');
        const streakCountEl = document.getElementById('settings-streak-count');
        const streakCountElVic = document.getElementById('settings-streak-count-victory');
        const orbits = document.querySelectorAll('.settings-streak-orbit');
        
        const hasSolvedAny = solvedList.size > 0;
        const { currentStreak } = calculateStreakMetrics(solvedList);
        
        if (hasSolvedAny && currentStreak > 0) {
            const streakStr = currentStreak.toLocaleString();
            
            // Check if animation has already played in this page load lifetime
            const animationPlayed = streakAnimationPlayed;
            
            // Hide normal profile icons, show streak counts and set their values
            if (profileIcon) {
                profileIcon.classList.add('hidden');
                const btn = profileIcon.closest('.settings-btn');
                if (animationPlayed) {
                    if (btn) btn.classList.add('animation-played');
                } else {
                    if (btn) btn.classList.remove('animation-played');
                }
            }
            if (profileIconVic) {
                profileIconVic.classList.add('hidden');
                const btn = profileIconVic.closest('.settings-btn');
                if (animationPlayed) {
                    if (btn) btn.classList.add('animation-played');
                } else {
                    if (btn) btn.classList.remove('animation-played');
                }
            }
            
            if (streakCountEl) {
                streakCountEl.innerText = streakStr;
                streakCountEl.classList.remove('hidden');
            }
            if (streakCountElVic) {
                streakCountElVic.innerText = streakStr;
                streakCountElVic.classList.remove('hidden');
            }
            
            // Show the confetti orbits
            orbits.forEach(orbit => orbit.classList.remove('hidden'));
            
            // Mark animation as played for this page load lifetime
            if (!animationPlayed) {
                streakAnimationPlayed = true;
            }
        } else {
            // Show normal profile icons, hide streak counts and orbits
            if (profileIcon) {
                profileIcon.classList.remove('hidden');
                const btn = profileIcon.closest('.settings-btn');
                if (btn) btn.classList.remove('animation-played');
            }
            if (profileIconVic) {
                profileIconVic.classList.remove('hidden');
                const btn = profileIconVic.closest('.settings-btn');
                if (btn) btn.classList.remove('animation-played');
            }
            
            if (streakCountEl) streakCountEl.classList.add('hidden');
            if (streakCountElVic) streakCountElVic.classList.add('hidden');
            
            orbits.forEach(orbit => orbit.classList.add('hidden'));
        }
    } catch (e) {
        console.error("Failed to update profile streak:", e);
    }
}


// ============================================================================
// WORLD TRAVEL MAP, COMPLETED PUZZLES LIST & 1-CLICK POSTCARD OVERLAY
// ============================================================================

const WORLD_MAP_WIDTH = 1000;
const WORLD_MAP_HEIGHT = 500;

// Fallback coordinate & location dictionary so solved pins render accurately even if a cached CDN JSON lacks lat/lng
const FALLBACK_LANDMARK_COORDS = {
    "acropolis of athens": [37.9715, 23.7257, "Athens, Greece"],
    "ait benhaddou": [31.047, -7.1319, "Ouarzazate, Morocco"],
    "alcatraz island": [37.827, -122.423, "San Francisco, California, USA"],
    "alhambra": [37.1761, -3.5881, "Granada, Spain"],
    "amalfi coast": [40.6333, 14.6029, "Campania, Italy"],
    "amazon rainforest": [-3.4653, -62.2159, "Amazonas, Brazil"],
    "angel falls": [5.9701, -62.5362, "Canaima National Park, Venezuela"],
    "angkor wat": [13.4125, 103.867, "Siem Reap, Cambodia"],
    "anne frank house": [52.3752, 4.884, "Amsterdam, Netherlands"],
    "antelope canyon": [36.8619, -111.3743, "Page, Arizona, USA"],
    "arashiyama bamboo grove": [35.0168, 135.6713, "Kyoto, Japan"],
    "arc de triomphe": [48.8738, 2.295, "Paris, France"],
    "atacama desert": [-23.8634, -69.1328, "Northern Chile"],
    "avenue of the baobabs": [-20.2508, 44.4184, "Menabe Region, Madagascar"],
    "ayutthaya historical park": [14.3566, 100.5586, "Ayutthaya, Thailand"],
    "bagan temples": [21.1717, 94.8585, "Bagan, Myanmar"],
    "banff national park": [51.4968, -115.9281, "Alberta, Canada"],
    "batu caves": [3.2379, 101.684, "Selangor, Malaysia"],
    "berlin wall memorial": [52.5351, 13.3903, "Berlin, Germany"],
    "big ben": [51.5007, -0.1246, "London, UK"],
    "black forest": [48.2775, 8.186, "Baden-Württemberg, Germany"],
    "blarney castle": [51.9291, -8.5709, "Blarney, Ireland"],
    "blue lagoon": [63.8804, -22.4495, "Reykjanes Peninsula, Iceland"],
    "blue mosque (sultan ahmed mosque)": [41.0054, 28.9768, "Istanbul, Turkey"],
    "bondi beach": [-33.8915, 151.2767, "Sydney, Australia"],
    "bora bora": [-16.5004, -151.7415, "French Polynesia"],
    "borobudur temple": [-7.6079, 110.2038, "Central Java, Indonesia"],
    "bran castle": [45.5149, 25.3672, "Bran, Romania"],
    "brandenburg gate": [52.5163, 13.3777, "Berlin, Germany"],
    "brooklyn bridge": [40.7061, -73.9969, "New York City, USA"],
    "buckingham palace": [51.5014, -0.1419, "London, England"],
    "burj al arab": [25.1412, 55.1852, "Dubai, UAE"],
    "burj khalifa": [25.1972, 55.2744, "Dubai, UAE"],
    "canals of amsterdam": [52.3676, 4.8945, "Amsterdam, Netherlands"],
    "cape of good hope": [-34.3568, 18.474, "Western Cape, South Africa"],
    "cappadocia": [38.6431, 34.8289, "Nevsehir Province, Turkey"],
    "casa rosada": [-34.6081, -58.3703, "Buenos Aires, Argentina"],
    "charles bridge": [50.0865, 14.4114, "Prague, Czech Republic"],
    "chichen itza": [20.6843, -88.5678, "Yucatan, Mexico"],
    "christ the redeemer": [-22.9519, -43.2105, "Rio de Janeiro, Brazil"],
    "cliffs of moher": [52.9715, -9.4309, "County Clare, Ireland"],
    "cloud gate": [41.8827, -87.6233, "Chicago, Illinois, USA"],
    "cn tower": [43.6426, -79.3871, "Toronto, Ontario, Canada"],
    "cologne cathedral": [50.9413, 6.9583, "Cologne, Germany"],
    "colosseum": [41.8902, 12.4922, "Rome, Italy"],
    "copacabana beach": [-22.9711, -43.1825, "Rio de Janeiro, Brazil"],
    "dead sea": [31.559, 35.4732, "Jordan / Israel"],
    "death road": [-16.3333, -67.8, "La Paz, Bolivia"],
    "denali national park": [63.1148, -151.1926, "Alaska, USA"],
    "dubai mall": [25.1975, 55.2797, "Dubai, UAE"],
    "dubrovnik old town": [42.641, 18.1072, "Dubrovnik, Croatia"],
    "dubrovnik old town walls": [42.641, 18.1072, "Dubrovnik, Croatia"],
    "duomo di firenze": [43.7731, 11.256, "Florence, Italy"],
    "easter island moai": [-27.1258, -109.2768, "Easter Island, Chile"],
    "edinburgh castle": [55.9486, -3.1999, "Edinburgh, Scotland"],
    "eiffel tower": [48.8584, 2.2945, "Paris, France"],
    "empire state building": [40.7484, -73.9857, "New York City, USA"],
    "ephesus ancient city": [37.9397, 27.3408, "Izmir Province, Turkey"],
    "everglades national park": [25.2866, -80.8987, "Florida, USA"],
    "forbidden city": [39.9163, 116.3972, "Beijing, China"],
    "french quarter": [29.9584, -90.0644, "New Orleans, Louisiana, USA"],
    "fushimi inari-taisha": [34.9671, 135.7727, "Kyoto, Japan"],
    "galapagos islands": [-0.9538, -90.9656, "Ecuador"],
    "gardens by the bay": [1.2816, 103.8636, "Singapore"],
    "gateway arch": [38.6247, -90.1848, "St. Louis, Missouri, USA"],
    "giant's causeway": [55.2408, -6.5116, "Northern Ireland, UK"],
    "golden gate bridge": [37.8199, -122.4783, "San Francisco, California, USA"],
    "golden temple (harmandir sahib)": [31.62, 74.8765, "Amritsar, Punjab, India"],
    "grand canal": [45.4375, 12.3327, "Venice, Italy"],
    "grand canyon": [36.1069, -112.1129, "Arizona, USA"],
    "grand place": [50.8467, 4.3525, "Brussels, Belgium"],
    "great barrier reef": [-18.2871, 147.6992, "Queensland, Australia"],
    "great blue hole": [17.3159, -87.5346, "Belize"],
    "great sphinx of giza": [29.9753, 31.1376, "Giza, Egypt"],
    "great wall of china": [40.4319, 116.5704, "Beijing / Huairou, China"],
    "guggenheim museum bilbao": [43.2687, -2.934, "Bilbao, Spain"],
    "gyeongbokgung palace": [37.5796, 126.977, "Seoul, South Korea"],
    "ha long bay": [20.9101, 107.1839, "Quang Ninh Province, Vietnam"],
    "hagia sophia": [41.0086, 28.9802, "Istanbul, Turkey"],
    "hallstatt": [47.5622, 13.6493, "Hallstatt, Austria"],
    "hawa mahal": [26.9239, 75.8267, "Jaipur, Rajasthan, India"],
    "himeji castle": [34.8394, 134.6939, "Hyogo Prefecture, Japan"],
    "hofbräuhaus münchen": [48.1376, 11.5798, "Munich, Germany"],
    "hoi an ancient town": [15.8801, 108.338, "Hoi An, Vietnam"],
    "hollywood sign": [34.1341, -118.3215, "Los Angeles, California, USA"],
    "hoover dam": [36.016, -114.7377, "Nevada / Arizona, USA"],
    "iguazu falls": [-25.6953, -54.4367, "Argentina / Brazil"],
    "itsukushima shrine": [34.296, 132.3198, "Miyajima, Japan"],
    "jemaa el-fnaa": [31.6258, -7.9891, "Marrakesh, Morocco"],
    "djemaa el-fna": [31.6258, -7.9891, "Marrakesh, Morocco"],
    "kremlin": [55.752, 37.6175, "Moscow, Russia"],
    "the kremlin": [55.752, 37.6175, "Moscow, Russia"],
    "kruger national park": [-23.9884, 31.5547, "South Africa"],
    "la rambla": [41.3809, 2.1735, "Barcelona, Spain"],
    "lake bled": [46.3625, 14.0936, "Bled, Slovenia"],
    "lake louise": [51.4167, -116.2167, "Alberta, Canada"],
    "lake titicaca": [-15.8422, -69.3354, "Puno, Peru / Bolivia"],
    "leaning tower of pisa": [43.723, 10.3966, "Pisa, Italy"],
    "liberty bell": [39.9496, -75.1503, "Philadelphia, Pennsylvania, USA"],
    "lincoln memorial": [38.8893, -77.0502, "Washington, D.C., USA"],
    "loch ness": [57.3229, -4.4244, "Scottish Highlands, Scotland"],
    "louvre museum": [48.8606, 2.3376, "Paris, France"],
    "luxor temple": [25.6995, 32.6391, "Luxor, Egypt"],
    "machu picchu": [-13.1631, -72.545, "Cusco Region, Peru"],
    "marina bay sands": [1.2834, 103.8607, "Singapore"],
    "matterhorn": [45.9766, 7.6585, "Zermatt, Switzerland"],
    "meteora": [39.7217, 21.6306, "Thessaly, Greece"],
    "milan cathedral": [45.4641, 9.1919, "Milan, Italy"],
    "milford sound": [-44.6414, 167.8974, "South Island, New Zealand"],
    "mont saint-michel": [48.6361, -1.5115, "Normandy, France"],
    "monument valley": [36.998, -110.0985, "Arizona / Utah, USA"],
    "mount everest": [27.9881, 86.925, "Himalayas, Nepal"],
    "mount fuji": [35.3606, 138.7274, "Honshu, Japan"],
    "mount kilimanjaro": [-3.0674, 37.3556, "Tanzania"],
    "mount rushmore": [43.8791, -103.4591, "South Dakota, USA"],
    "nazca lines": [-14.739, -75.13, "Nazca, Peru"],
    "neuschwanstein castle": [47.5576, 10.7498, "Bavaria, Germany"],
    "ngorongoro crater": [-3.1618, 35.5877, "Tanzania"],
    "niagara falls": [43.0962, -79.0377, "New York, USA / Ontario, Canada"],
    "notre-dame cathedral": [48.853, 2.3499, "Paris, France"],
    "okavango delta": [-19.2833, 22.9, "Botswana"],
    "old havana": [23.1367, -82.3503, "Havana, Cuba"],
    "oriental pearl tv tower": [31.2397, 121.4998, "Shanghai, China"],
    "osaka castle": [34.6873, 135.5262, "Osaka, Japan"],
    "palace of versailles": [48.8049, 2.1204, "Versailles, France"],
    "palm jumeirah": [25.1124, 55.139, "Dubai, UAE"],
    "pamukkale": [37.9237, 29.1244, "Denizli Province, Turkey"],
    "panama canal": [9.08, -79.68, "Panama City, Panama"],
    "pantheon": [41.8986, 12.4769, "Rome, Italy"],
    "parthenon": [37.9715, 23.7267, "Athens, Greece"],
    "perito moreno glacier": [-50.4957, -73.1376, "Patagonia, Argentina"],
    "petra": [30.3285, 35.4444, "Ma'an Governorate, Jordan"],
    "petronas twin towers": [3.1579, 101.7116, "Kuala Lumpur, Malaysia"],
    "plitvice lakes national park": [44.8654, 15.582, "Croatia"],
    "pompeii": [40.7509, 14.487, "Campania, Italy"],
    "potala palace": [29.6555, 91.1186, "Lhasa, Tibet"],
    "prague castle": [50.0911, 14.4016, "Prague, Czech Republic"],
    "pulpit rock (preikestolen)": [58.9864, 6.1904, "Rogaland, Norway"],
    "pyramids of giza": [29.9792, 31.1342, "Giza, Egypt"],
    "red square": [55.7539, 37.6208, "Moscow, Russia"],
    "roman baths": [51.3811, -2.3596, "Bath, England"],
    "roman forum": [41.8925, 12.4853, "Rome, Italy"],
    "sagrada familia": [41.4036, 2.1744, "Barcelona, Spain"],
    "sagrada família": [41.4036, 2.1744, "Barcelona, Spain"],
    "salar de uyuni": [-20.1338, -67.4891, "Uyuni, Bolivia"],
    "san antonio river walk": [29.4241, -98.4886, "San Antonio, Texas, USA"],
    "santorini": [36.3932, 25.4615, "Cyclades, Greece"],
    "selaron steps": [-22.9153, -43.1792, "Rio de Janeiro, Brazil"],
    "senso-ji temple": [35.7148, 139.7967, "Tokyo, Japan"],
    "serengeti national park": [-2.3333, 34.8333, "Tanzania"],
    "sheikh zayed grand mosque": [24.4128, 54.475, "Abu Dhabi, UAE"],
    "shibuya crossing": [35.6595, 139.7004, "Tokyo, Japan"],
    "shwedagon pagoda": [16.7983, 96.1497, "Yangon, Myanmar"],
    "sigiriya": [7.957, 80.7603, "Central Province, Sri Lanka"],
    "sky tower": [-36.8485, 174.7622, "Auckland, New Zealand"],
    "space needle": [47.6205, -122.3493, "Seattle, Washington, USA"],
    "spanish steps": [41.906, 12.4828, "Rome, Italy"],
    "st. basil's cathedral": [55.7525, 37.6231, "Moscow, Russia"],
    "st. mark's square": [45.4342, 12.3385, "Venice, Italy"],
    "st. peter's basilica": [41.9022, 12.4539, "Vatican City"],
    "statue of liberty": [40.6892, -74.0445, "New York City, USA"],
    "stonehenge": [51.1789, -1.8262, "Wiltshire, England"],
    "sugarloaf mountain": [-22.9493, -43.1546, "Rio de Janeiro, Brazil"],
    "summer palace": [39.9999, 116.2755, "Beijing, China"],
    "sydney harbour bridge": [-33.8523, 151.2108, "Sydney, Australia"],
    "sydney opera house": [-33.8568, 151.2153, "Sydney, Australia"],
    "table mountain": [-33.9628, 18.4098, "Cape Town, South Africa"],
    "taipei 101": [25.0339, 121.5645, "Taipei, Taiwan"],
    "taj mahal": [27.1751, 78.0421, "Agra, India"],
    "tanah lot temple": [-8.6212, 115.0868, "Bali, Indonesia"],
    "temple of heaven": [39.8822, 116.4066, "Beijing, China"],
    "teotihuacan": [19.6925, -98.8438, "Mexico City, Mexico"],
    "terracotta army": [34.3841, 109.2785, "Xi'an, China"],
    "the acropolis of athens": [37.9715, 23.7257, "Athens, Greece"],
    "the alamo": [29.426, -98.4861, "San Antonio, Texas, USA"],
    "the blue lagoon": [63.8804, -22.4495, "Grindavik, Iceland"],
    "the bund": [31.24, 121.49, "Shanghai, China"],
    "the dead sea": [31.559, 35.4732, "Jordan / Israel"],
    "the las vegas strip": [36.1147, -115.1728, "Las Vegas, Nevada, USA"],
    "the shard": [51.5045, -0.0865, "London, England"],
    "the strip, las vegas": [36.1147, -115.1728, "Las Vegas, Nevada, USA"],
    "tiger's nest monastery": [27.4919, 89.3634, "Paro Valley, Bhutan"],
    "tikal": [17.222, -89.6237, "Peten, Guatemala"],
    "times square": [40.758, -73.9855, "New York City, USA"],
    "tokyo tower": [35.6586, 139.7454, "Tokyo, Japan"],
    "torres del paine national park": [-50.9423, -73.4068, "Patagonia, Chile"],
    "tower bridge": [51.5055, -0.0754, "London, UK"],
    "tower of london": [51.5081, -0.0759, "London, England"],
    "trevi fountain": [41.9009, 12.4833, "Rome, Italy"],
    "tulum ruins": [20.2149, -87.4293, "Tulum, Mexico"],
    "twelve apostles": [-38.6621, 143.1051, "Victoria, Australia"],
    "uluru (ayers rock)": [-25.3444, 131.0369, "Northern Territory, Australia"],
    "valley of the kings": [25.7402, 32.6014, "Luxor, Egypt"],
    "vatican museums": [41.9065, 12.4536, "Vatican City"],
    "victoria falls": [-17.9243, 25.8572, "Zambia / Zimbabwe"],
    "victoria peak": [22.2759, 114.1455, "Hong Kong"],
    "wadi rum": [29.5765, 35.4208, "Jordan"],
    "waitomo glowworm caves": [-38.2608, 175.1036, "North Island, New Zealand"],
    "walled city of cartagena": [10.4236, -75.5503, "Cartagena, Colombia"],
    "walls of dubrovnik": [42.641, 18.1072, "Dubrovnik, Croatia"],
    "washington monument": [38.8895, -77.0353, "Washington, D.C., USA"],
    "wat arun": [13.7437, 100.4889, "Bangkok, Thailand"],
    "westminster abbey": [51.4994, -0.1273, "London, England"],
    "white house": [38.8977, -77.0365, "Washington, D.C., USA"],
    "windsor castle": [51.4839, -0.6044, "Windsor, England"],
    "yellowstone national park": [44.428, -110.5885, "Wyoming, USA"],
    "yosemite national park": [37.8651, -119.5383, "California, USA"],
    "zhangjiajie national forest park": [29.3167, 110.4333, "Hunan, China"],
    "mount kenya": [-0.1521, 37.3084, "Kenya"],
    "registan square": [39.6548, 66.9757, "Samarkand, Uzbekistan"],
    "arenal volcano": [10.4626, -84.7032, "Alajuela Province, Costa Rica"],
    "the pitons": [13.8094, -61.0669, "Soufrière, St. Lucia"],
    "cerro monserrate": [4.6057, -74.0555, "Bogotá, Colombia"],
    "uluru": [-25.3444, 131.0369, "Northern Territory, Australia"],
    "geirangerfjord": [62.1015, 7.0941, "Møre og Romsdal, Norway"],
    "fisherman's bastion": [47.5022, 19.0348, "Budapest, Hungary"],
    "paro taktsang (tiger's nest monastery)": [27.4919, 89.3634, "Paro Valley, Bhutan"],
    "tiger's nest monastery (paro taktsang)": [27.4919, 89.3634, "Paro Valley, Bhutan"],
    "dunn's river falls": [18.4148, -77.1394, "Ocho Rios, Jamaica"],
    "prague astronomical clock": [50.0870, 14.4207, "Prague, Czech Republic"],
    "pyramids of meroë": [16.9380, 33.7489, "Meroë, Sudan"],
    "pyramids of meroe": [16.9380, 33.7489, "Meroë, Sudan"],
    "denali (mount mckinley)": [63.0695, -151.0074, "Alaska, USA"],
    "white temple (wat rong khun)": [19.8242, 99.7631, "Chiang Rai, Thailand"]
};

// Self-contained geographic continent polygons in [lng, lat] coordinates
// Projected via projectLatLngToMap(lat, lng) so continents and landmark pins share the exact same coordinate frame
const WORLD_CONTINENT_POLYGONS = [
    // North America & Central America
    [
        [-168, 66], [-162, 70], [-156, 71], [-140, 70], [-128, 70], [-115, 68], [-95, 68], [-82, 67],
        [-78, 63], [-80, 55], [-77, 58], [-68, 60], [-64, 60], [-56, 52], [-53, 47], [-60, 46],
        [-66, 44], [-70, 42], [-74, 40], [-76, 35], [-80, 32], [-80, 25], [-82, 25], [-83, 30],
        [-89, 30], [-95, 29], [-97, 26], [-96, 19], [-90, 21], [-87, 21], [-88, 16], [-83, 15],
        [-83, 10], [-79, 9], [-77, 8], [-80, 8], [-84, 9], [-88, 13], [-93, 15], [-97, 16],
        [-105, 20], [-109, 24], [-112, 31], [-115, 30], [-110, 23], [-114, 27], [-117, 33],
        [-122, 37], [-124, 42], [-124, 48], [-130, 54], [-138, 59], [-148, 61], [-152, 59],
        [-161, 56], [-165, 60], [-166, 64]
    ],
    // Greenland
    [
        [-72, 78], [-58, 82], [-34, 83], [-20, 81], [-18, 75], [-22, 70], [-36, 65], [-44, 60],
        [-50, 62], [-54, 68], [-60, 75]
    ],
    // Baffin & Canadian Arctic Archipelago
    [
        [-85, 73], [-74, 73], [-64, 66], [-66, 62], [-76, 64], [-84, 69]
    ],
    [
        [-118, 74], [-98, 76], [-92, 71], [-108, 69], [-118, 71]
    ],
    // Cuba & Hispaniola
    [
        [-85, 22], [-79, 23], [-74, 20], [-78, 20], [-84, 21]
    ],
    [
        [-74, 19.8], [-68.5, 18.6], [-71.5, 17.8], [-74.4, 18.4]
    ],
    // South America
    [
        [-77, 8], [-75, 11], [-71, 12], [-62, 11], [-52, 5], [-48, 0], [-42, -3], [-35, -6],
        [-35, -10], [-39, -15], [-40, -21], [-43, -23], [-48, -26], [-52, -32], [-58, -35],
        [-57, -38], [-62, -40], [-65, -43], [-66, -48], [-68, -52], [-66, -55], [-72, -54],
        [-75, -48], [-73, -40], [-72, -33], [-70, -24], [-71, -18], [-76, -14], [-80, -8],
        [-81, -4], [-80, 0], [-78, 4]
    ],
    // Iceland
    [
        [-24, 65.5], [-14, 66], [-13.5, 64], [-22, 63.5]
    ],
    // Great Britain & Ireland
    [
        [-6, 58.5], [-2, 57.5], [-1, 54], [1.5, 52.5], [1, 51], [-5, 50], [-5.5, 52], [-3, 53.5],
        [-5, 55], [-6, 57]
    ],
    [
        [-10, 54.5], [-6, 55], [-6, 52], [-10, 51.5]
    ],
    // Continental Europe & Scandinavia
    [
        [-9, 43], [-9, 37], [-5, 36], [0, 38], [3, 42], [5, 43], [8, 44], [12, 41], [16, 38],
        [18, 40], [15, 42], [13, 45], [15, 44], [20, 39], [23, 37], [26, 40], [28, 41], [29, 44],
        [31, 46], [38, 47], [42, 44], [48, 46], [52, 55], [58, 68], [42, 68], [34, 69], [28, 71],
        [18, 69], [10, 63], [5, 60], [7, 58], [11, 59], [12, 56], [17, 56], [20, 63], [24, 65],
        [28, 60], [22, 59], [20, 55], [14, 54], [9, 55], [8, 54], [4, 52], [1, 50], [-2, 48],
        [-1, 44], [-4, 43]
    ],
    // Africa
    [
        [-6, 36], [5, 37], [10, 37], [11, 33], [20, 32], [25, 32], [32, 31], [34, 28], [38, 22],
        [41, 15], [43, 12], [51, 12], [49, 6], [42, 0], [40, -6], [40, -15], [35, -20], [35, -25],
        [31, -30], [26, -34], [18, -35], [17, -29], [14, -22], [12, -16], [12, -6], [9, 0],
        [9, 4], [4, 6], [-2, 5], [-8, 4], [-13, 8], [-17, 15], [-16, 21], [-13, 27], [-10, 31]
    ],
    // Madagascar
    [
        [49, -12], [50, -16], [47, -25], [44, -25], [44, -18], [47, -14]
    ],
    // Middle East, Asia, India & Indochina
    [
        [26, 40], [35, 42], [42, 42], [48, 46], [52, 55], [58, 68], [72, 72], [90, 74], [110, 74],
        [135, 71], [160, 69], [178, 66], [170, 60], [162, 56], [156, 51], [160, 56], [148, 59],
        [140, 54], [141, 48], [135, 43], [130, 42], [128, 35], [126, 37], [124, 40], [121, 39],
        [118, 38], [122, 35], [122, 30], [118, 24], [110, 20], [106, 21], [108, 16], [109, 12],
        [105, 9], [103, 13], [100, 13], [99, 8], [103, 2], [101, 4], [98, 10], [97, 16], [94, 16],
        [92, 21], [88, 22], [85, 19], [80, 14], [78, 8], [75, 12], [72, 21], [68, 24], [62, 25],
        [56, 27], [51, 29], [48, 30], [50, 26], [55, 24], [60, 22], [54, 17], [45, 13], [43, 13],
        [40, 18], [36, 27], [34, 28], [35, 32], [36, 36], [28, 36], [26, 39]
    ],
    // Sri Lanka
    [
        [80, 9.8], [81.8, 7.5], [80.5, 6], [79.8, 7.5]
    ],
    // Japan (Hokkaido, Honshu, Kyushu)
    [
        [140.5, 44.5], [145, 44], [144, 42], [140, 41.5]
    ],
    [
        [140.5, 41], [142, 39], [140.5, 35.5], [136, 34.5], [131, 34], [130, 31.5], [131.5, 31],
        [134, 33.5], [137, 37], [139.5, 39.5]
    ],
    // Taiwan
    [
        [121, 25.2], [122, 24], [120.8, 22], [120.2, 23.5]
    ],
    // Philippines
    [
        [120.5, 18.5], [122.5, 16], [124, 13], [126, 10], [125.5, 6.5], [122, 7], [121, 12], [119.8, 15]
    ],
    // Sumatra, Java, Borneo, Sulawesi, New Guinea
    [
        [95.5, 5.5], [102, 1], [106, -5.5], [104, -6], [99, -1], [95.5, 3.5]
    ],
    [
        [105.5, -6], [114.5, -7.8], [114, -8.7], [106, -7]
    ],
    [
        [109, 2], [115, 5.5], [118.5, 4.5], [117.5, -1], [114.5, -3.5], [110, -2.5]
    ],
    [
        [119.5, 1], [125, 1.5], [122.5, -4.5], [119.5, -5], [119, -2]
    ],
    [
        [131, -1], [141, -2.5], [148, -6], [150.5, -10], [146, -9], [141, -8], [135, -4.5]
    ],
    // Australia & Tasmania
    [
        [114, -22], [122, -17], [127, -14], [131, -12], [136, -12], [136, -15], [140, -17],
        [142, -11], [145, -15], [150, -21], [153, -27], [151, -34], [148, -38], [143, -39],
        [139, -36], [135, -34], [130, -32], [123, -34], [115, -34], [114, -28]
    ],
    [
        [145, -40.8], [148.3, -41], [147.5, -43.5], [145.3, -43]
    ],
    // New Zealand (North & South Islands)
    [
        [173, -35], [178, -37.5], [175, -41.5], [174, -39.5], [174.5, -37]
    ],
    [
        [173, -41], [174, -42.5], [170.5, -46], [166.5, -46], [168, -44], [171.5, -41.5]
    ],
    // Antarctica
    [
        [-180, -84], [-150, -76], [-120, -74], [-90, -73], [-65, -65], [-58, -64], [-60, -72],
        [-30, -75], [0, -70], [35, -68], [70, -68], [105, -66], [140, -67], [170, -72],
        [165, -78], [180, -78], [180, -88], [-180, -88]
    ]
];

const WORLD_MAP_REGIONS = {
    world: { scale: 1, tx: 0, ty: 0 },
    americas: { scale: 2.0, centerLat: 10, centerLng: -85 },
    europe: { scale: 3.7, centerLat: 47, centerLng: 12 },
    africa_me: { scale: 2.25, centerLat: 8, centerLng: 25 },
    asia_oceania: { scale: 2.05, centerLat: 10, centerLng: 118 }
};

let worldMapState = {
    initialized: false,
    scale: 1,
    tx: 0,
    ty: 0,
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    startTx: 0,
    startTy: 0,
    dragMoved: false,
    activePostcardChallenge: null
};

function projectLatLngToMap(lat, lng) {
    const clampedLat = Math.max(-85, Math.min(85, Number(lat) || 0));
    const normLng = ((((Number(lng) || 0) + 180) % 360) + 360) % 360 - 180;
    const x = ((normLng + 180) / 360) * WORLD_MAP_WIDTH;
    const y = ((90 - clampedLat) / 180) * WORLD_MAP_HEIGHT;
    return { x, y };
}

function getChallengeCoordinates(challenge) {
    if (!challenge) return null;
    if (typeof challenge.lat === 'number' && typeof challenge.lng === 'number' && !isNaN(challenge.lat) && !isNaN(challenge.lng)) {
        return {
            lat: challenge.lat,
            lng: challenge.lng,
            location: challenge.location || ""
        };
    }
    const key = String(challenge.boss_original_title || '').trim().toLowerCase();
    const fallback = FALLBACK_LANDMARK_COORDS[key];
    if (fallback) {
        return {
            lat: fallback[0],
            lng: fallback[1],
            location: challenge.location || fallback[2] || ""
        };
    }
    return null;
}

function renderBaseWorldMapSVG() {
    const graticuleEl = document.getElementById('world-map-graticule');
    const landEl = document.getElementById('world-map-land');
    if (!graticuleEl || !landEl) return;

    // 1. Graticule lines every 30 deg + Equator & Tropics
    let gratHtml = '';
    for (let lng = -150; lng <= 150; lng += 30) {
        const { x } = projectLatLngToMap(0, lng);
        gratHtml += `<line x1="${x.toFixed(1)}" y1="0" x2="${x.toFixed(1)}" y2="${WORLD_MAP_HEIGHT}" class="world-map-graticule-line" />`;
    }
    for (let lat = -60; lat <= 60; lat += 30) {
        if (lat === 0) continue;
        const { y } = projectLatLngToMap(lat, 0);
        gratHtml += `<line x1="0" y1="${y.toFixed(1)}" x2="${WORLD_MAP_WIDTH}" y2="${y.toFixed(1)}" class="world-map-graticule-line" />`;
    }
    // Equator & Tropics
    [0, 23.436, -23.436].forEach(lat => {
        const { y } = projectLatLngToMap(lat, 0);
        gratHtml += `<line x1="0" y1="${y.toFixed(1)}" x2="${WORLD_MAP_WIDTH}" y2="${y.toFixed(1)}" class="world-map-equator-line" />`;
    });
    graticuleEl.innerHTML = gratHtml;

    // 2. Continent & Island Polygons
    let landHtml = '';
    WORLD_CONTINENT_POLYGONS.forEach(poly => {
        const d = poly.map((pt, idx) => {
            const { x, y } = projectLatLngToMap(pt[1], pt[0]);
            return `${idx === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(' ') + ' Z';
        landHtml += `<path d="${d}" class="world-map-continent" />`;
    });
    landEl.innerHTML = landHtml;
}

function clampWorldMapTransform() {
    const s = Math.max(1, Math.min(8, worldMapState.scale));
    worldMapState.scale = s;
    const minTx = WORLD_MAP_WIDTH * (1 - s);
    const minTy = WORLD_MAP_HEIGHT * (1 - s);
    worldMapState.tx = Math.max(minTx, Math.min(0, worldMapState.tx));
    worldMapState.ty = Math.max(minTy, Math.min(0, worldMapState.ty));
}

function applyWorldMapTransform() {
    clampWorldMapTransform();
    const camera = document.getElementById('world-map-camera');
    if (camera) {
        camera.setAttribute(
            'transform',
            `translate(${worldMapState.tx.toFixed(2)}, ${worldMapState.ty.toFixed(2)}) scale(${worldMapState.scale.toFixed(3)})`
        );
    }
    // Keep pin markers crisp and well-proportioned across zoom levels
    const invScale = 1 / Math.pow(worldMapState.scale, 0.62);
    document.querySelectorAll('#world-map-pins .map-pin-scale-wrap').forEach(el => {
        el.setAttribute('transform', `scale(${invScale.toFixed(3)})`);
    });
}

function setWorldMapRegion(regionKey) {
    const preset = WORLD_MAP_REGIONS[regionKey] || WORLD_MAP_REGIONS.world;
    if (regionKey === 'world' || !preset.centerLat) {
        worldMapState.scale = 1;
        worldMapState.tx = 0;
        worldMapState.ty = 0;
    } else {
        const { x, y } = projectLatLngToMap(preset.centerLat, preset.centerLng);
        worldMapState.scale = preset.scale;
        worldMapState.tx = (WORLD_MAP_WIDTH / 2) - x * preset.scale;
        worldMapState.ty = (WORLD_MAP_HEIGHT / 2) - y * preset.scale;
    }
    applyWorldMapTransform();

    document.querySelectorAll('#world-map-region-pills .map-region-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.region === regionKey);
    });
}

function zoomWorldMapBy(factor, focalSvgX = WORLD_MAP_WIDTH / 2, focalSvgY = WORLD_MAP_HEIGHT / 2) {
    const oldScale = worldMapState.scale;
    const newScale = Math.max(1, Math.min(8, oldScale * factor));
    if (Math.abs(newScale - oldScale) < 0.001) return;

    const mapX = (focalSvgX - worldMapState.tx) / oldScale;
    const mapY = (focalSvgY - worldMapState.ty) / oldScale;

    worldMapState.scale = newScale;
    worldMapState.tx = focalSvgX - mapX * newScale;
    worldMapState.ty = focalSvgY - mapY * newScale;
    applyWorldMapTransform();
}

function renderSolvedMapPinsAndList() {
    const pinsLayer = document.getElementById('world-map-pins');
    const listContainer = document.getElementById('map-completed-list');
    const emptyHint = document.getElementById('world-map-empty-hint');
    if (!pinsLayer || !listContainer) return;

    const solvedSet = getSolvedPuzzlesList();
    const solvedHints = getSolvedHintsMap();
    const approved = getApprovedChallenges();

    const solvedChallenges = approved.filter(c => solvedSet.has(padPuzzleNumber(c.puzzle_number)));
    // Sort newest solved challenge first for the list
    const solvedChallengesDesc = [...solvedChallenges].sort(
        (a, b) => parseInt(b.puzzle_number) - parseInt(a.puzzle_number)
    );

    updateWorldMapBadges();

    if (emptyHint) {
        emptyHint.classList.toggle('hidden', solvedChallenges.length > 0);
    }

    // Group pins by proximity so multi-puzzle landmarks (e.g. Eiffel Tower, Rome) fan out cleanly
    const pinItems = [];
    solvedChallenges.forEach(c => {
        const coords = getChallengeCoordinates(c);
        if (!coords) return;
        const pt = projectLatLngToMap(coords.lat, coords.lng);
        pinItems.push({
            challenge: c,
            coords,
            baseX: pt.x,
            baseY: pt.y,
            x: pt.x,
            y: pt.y
        });
    });

    // Cluster pins within 6 SVG units and apply deterministic radial micro-offset
    const clusters = [];
    pinItems.forEach(item => {
        let matchedCluster = clusters.find(cl => {
            const dx = cl.cx - item.baseX;
            const dy = cl.cy - item.baseY;
            return Math.sqrt(dx * dx + dy * dy) < 5.5;
        });
        if (!matchedCluster) {
            matchedCluster = { cx: item.baseX, cy: item.baseY, items: [] };
            clusters.push(matchedCluster);
        }
        matchedCluster.items.push(item);
    });

    clusters.forEach(cluster => {
        if (cluster.items.length > 1) {
            const radius = Math.min(11, 5.2 + cluster.items.length * 1.1);
            cluster.items.forEach((item, idx) => {
                const angle = (2 * Math.PI * idx) / cluster.items.length - Math.PI / 2;
                item.x = cluster.cx + Math.cos(angle) * radius;
                item.y = cluster.cy + Math.sin(angle) * radius;
                item.clustered = true;
            });
        }
    });

    const invScale = 1 / Math.pow(worldMapState.scale, 0.62);
    pinsLayer.innerHTML = '';

    pinItems.forEach(item => {
        const c = item.challenge;
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'map-pin-group');
        g.setAttribute('transform', `translate(${item.x.toFixed(2)}, ${item.y.toFixed(2)})`);
        g.setAttribute('tabindex', '0');
        g.setAttribute('role', 'button');
        g.setAttribute('aria-label', `Challenge #${c.puzzle_number}: ${c.boss_pun_title} (${c.boss_original_title})`);
        g.dataset.puzzleNumber = c.puzzle_number;

        const hints = solvedHints[padPuzzleNumber(c.puzzle_number)];
        const pinColor = hints === 0 ? '#06D6A0' : '#ff4757';

        let spokeLineHtml = '';
        if (item.clustered) {
            const dx = (item.baseX - item.x).toFixed(2);
            const dy = (item.baseY - item.y).toFixed(2);
            spokeLineHtml = `<line x1="0" y1="0" x2="${dx}" y2="${dy}" stroke="#2D3436" stroke-width="0.9" stroke-dasharray="1.5 1.5" opacity="0.65" />`;
        }

        g.innerHTML = `
            ${spokeLineHtml}
            <g class="map-pin-scale-wrap" transform="scale(${invScale.toFixed(3)})">
                <circle class="map-pin-pulse" cx="0" cy="0" r="8"></circle>
                <g class="map-pin-marker">
                    <path d="M0,0 C-3.8,-4.5 -7.5,-8.8 -7.5,-13.2 A7.5,7.5 0 1,1 7.5,-13.2 C7.5,-8.8 3.8,-4.5 0,0 Z"
                          fill="${pinColor}" stroke="#2D3436" stroke-width="1.8" stroke-linejoin="round" />
                    <circle cx="0" cy="-13.2" r="3" fill="#FAF8F5" stroke="#2D3436" stroke-width="1.2" />
                </g>
            </g>
        `;

        g.addEventListener('mouseenter', (ev) => showWorldMapPinTooltip(item, ev));
        g.addEventListener('mouseleave', hideWorldMapPinTooltip);
        g.addEventListener('focus', (ev) => showWorldMapPinTooltip(item, ev));
        g.addEventListener('blur', hideWorldMapPinTooltip);
        g.addEventListener('click', (ev) => {
            ev.stopPropagation();
            if (worldMapState.dragMoved) return;
            hideWorldMapPinTooltip();
            openMapPostcardOverlay(c);
        });
        g.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault();
                openMapPostcardOverlay(c);
            }
        });

        pinsLayer.appendChild(g);
    });

    // Populate Completed Puzzles List below the map
    listContainer.innerHTML = '';
    if (solvedChallengesDesc.length === 0) {
        listContainer.innerHTML = `
            <div style="text-align: center; padding: 18px 12px; color: var(--text-secondary); font-weight: 700; font-size: 0.85rem;">
                You haven't completed any puzzles yet. Solve today's challenge to start your collection!
            </div>
        `;
        return;
    }

    solvedChallengesDesc.forEach(c => {
        const coords = getChallengeCoordinates(c);
        const locLabel = coords && coords.location ? ` • ${coords.location}` : '';
        const row = document.createElement('div');
        row.className = 'map-completed-row';
        const thumbUrl = getCorrectPosterUrl(c.boss_poster_url);

        row.innerHTML = `
            <img src="${thumbUrl}" class="map-completed-thumb" alt="${c.boss_pun_title}" loading="lazy">
            <div class="map-completed-meta">
                <span class="map-completed-title">#${c.puzzle_number} — ${c.boss_pun_title}</span>
                <span class="map-completed-sub">📍 ${c.boss_original_title}${locLabel}</span>
            </div>
            <span class="map-completed-view-pill">🖼️ Postcard</span>
        `;

        row.addEventListener('mouseenter', () => {
            const pinEl = pinsLayer.querySelector(`.map-pin-group[data-puzzle-number="${c.puzzle_number}"]`);
            if (pinEl) pinEl.classList.add('highlighted');
        });
        row.addEventListener('mouseleave', () => {
            const pinEl = pinsLayer.querySelector(`.map-pin-group[data-puzzle-number="${c.puzzle_number}"]`);
            if (pinEl) pinEl.classList.remove('highlighted');
        });
        row.addEventListener('click', () => {
            openMapPostcardOverlay(c);
        });

        listContainer.appendChild(row);
    });
}

function showWorldMapPinTooltip(pinItem, ev) {
    const tooltip = document.getElementById('world-map-tooltip');
    const viewport = document.getElementById('world-map-viewport');
    const svg = document.getElementById('world-map-svg');
    if (!tooltip || !viewport || !svg) return;

    const c = pinItem.challenge;
    const locSuffix = pinItem.coords.location ? ` (${pinItem.coords.location})` : '';
    tooltip.innerHTML = `
        <span class="world-map-tooltip-pun">#${c.puzzle_number}: ${c.boss_pun_title}</span>
        <span class="world-map-tooltip-real">📍 ${c.boss_original_title}${locSuffix}</span>
    `;

    // Position tooltip in viewport pixel coordinates
    const svgRect = svg.getBoundingClientRect();
    const vpRect = viewport.getBoundingClientRect();
    const screenX = ((pinItem.x * worldMapState.scale + worldMapState.tx) / WORLD_MAP_WIDTH) * svgRect.width + (svgRect.left - vpRect.left);
    const screenY = ((pinItem.y * worldMapState.scale + worldMapState.ty) / WORLD_MAP_HEIGHT) * svgRect.height + (svgRect.top - vpRect.top);

    const clampedLeft = Math.max(85, Math.min(vpRect.width - 85, screenX));
    const clampedTop = Math.max(48, screenY);

    tooltip.style.left = `${clampedLeft}px`;
    tooltip.style.top = `${clampedTop}px`;
    tooltip.classList.remove('hidden');
}

function hideWorldMapPinTooltip() {
    const tooltip = document.getElementById('world-map-tooltip');
    if (tooltip) tooltip.classList.add('hidden');
}

function openMapPostcardOverlay(challenge) {
    if (!challenge) return;
    const modal = document.getElementById('map-postcard-modal');
    if (!modal) return;

    worldMapState.activePostcardChallenge = challenge;

    const coords = getChallengeCoordinates(challenge);
    const locStr = coords && coords.location ? coords.location : '';

    const headerBadge = document.getElementById('map-pc-header-badge');
    if (headerBadge) {
        headerBadge.innerHTML = `<span class="challenge-label">Challenge</span> #<span class="level-indicator-num">${challenge.puzzle_number}</span>${locStr ? ' • ' + locStr : ''}`;
    }

    const solvedStatusEl = document.getElementById('map-pc-solved-status');
    if (solvedStatusEl) {
        const solvedHints = getSolvedHintsMap();
        const hUsed = solvedHints[padPuzzleNumber(challenge.puzzle_number)];
        let statusText = '🎉 YOU SOLVED THIS CHALLENGE!';
        if (hUsed === 0) statusText = '🏆 SOLVED WITH NO HINTS!';
        else if (hUsed === 1) statusText = '🥇 SOLVED WITH 1 HINT!';
        else if (hUsed === 2) statusText = '🥈 SOLVED WITH 2 HINTS!';
        else if (hUsed === 3) statusText = '🥉 SOLVED WITH 3 HINTS!';
        else if (hUsed === 4) statusText = '⚡ SOLVED WITH 4 HINTS!';
        solvedStatusEl.innerText = statusText;
    }

    const posterImg = document.getElementById('map-pc-poster-img');
    if (posterImg) {
        posterImg.src = getCorrectPosterUrl(challenge.boss_poster_url);
        posterImg.onclick = () => {
            const fullModal = document.getElementById('poster-modal');
            const fullModalImg = document.getElementById('modal-poster-img');
            if (fullModal && fullModalImg && posterImg.src) {
                fullModalImg.src = posterImg.src;
                fullModal.classList.add('active');
            }
        };
    }

    const punTitleEl = document.getElementById('map-pc-pun-title');
    if (punTitleEl) punTitleEl.innerText = challenge.boss_pun_title || '';

    const reviewsBox = document.getElementById('map-pc-reviews-box');
    const toggleReviewsBtn = document.getElementById('btn-map-pc-toggle-reviews');
    if (reviewsBox && toggleReviewsBtn) {
        reviewsBox.classList.add('hidden');
        toggleReviewsBtn.innerText = '1-Star Reviews ▼';
        reviewsBox.innerHTML = `
            <div style="font-family: var(--font-body); font-size: 0.9rem; line-height: 1.4; color: #ff4757; text-align: left;">
                <strong style="color: #ff4757; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">1-Star Reviews:</strong>
                <ul style="margin: 5px 0 0 15px; padding: 0; color: #ff4757; font-weight: 700; list-style-type: disc;">
                    <li style="margin-bottom: 6px;">"${challenge.clue1 || ''}"</li>
                    <li style="margin-bottom: 6px;">"${challenge.clue2 || ''}"</li>
                    <li style="margin-bottom: 0;">"${challenge.clue3 || ''}"</li>
                </ul>
            </div>
        `;
    }

    const ownerReplyEl = document.getElementById('map-pc-owner-reply');
    if (ownerReplyEl) {
        ownerReplyEl.innerHTML = `
            <div style="text-align: left; width: 100%;">
                <strong style="color: var(--accent-main); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">Response from the Owner:</strong>
                <em style="color: #4a5568; display: block; font-style: italic; font-family: var(--font-body); line-height: 1.45; font-size: 0.9rem; font-weight: 600;">
                    "${challenge.boss_pitch || 'No response.'}"
                </em>
            </div>
        `;
    }

    const realLandmarkEl = document.getElementById('map-pc-real-landmark');
    if (realLandmarkEl) {
        realLandmarkEl.innerText = `Real Location: ${challenge.boss_original_title}${locStr ? ' (' + locStr + ')' : ''}`;
    }

    const cleanName = (challenge.boss_original_title || '').trim();
    const wikiSlug = cleanName.replace(/\s+/g, '_');
    const wikiLink = document.getElementById('map-pc-link-wiki');
    const mapsLink = document.getElementById('map-pc-link-maps');
    if (wikiLink) wikiLink.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(wikiSlug)}`;
    if (mapsLink) mapsLink.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanName + ' landmark')}`;

    const shareBtn = document.getElementById('btn-map-pc-share');
    if (shareBtn) {
        shareBtn.onclick = () => {
            const solvedHints = getSolvedHintsMap();
            const hUsed = solvedHints[padPuzzleNumber(challenge.puzzle_number)] ?? 0;
            const hintText = hUsed === 0 ? "No hints used! Perfect score! 🌟" : `${hUsed}/4 hints used 💡`;
            const copyText =
                `PunFiction Daily Challenge #${challenge.puzzle_number} 🗺️\n` +
                `Parody Solved: "${getMaskedParodyTitle(challenge.boss_pun_title)}"\n` +
                `Stats: ${hintText}\n` +
                `Play daily challenge at: https://iwandres.github.io/PunFiction/travelreviews/`;
            navigator.clipboard.writeText(copyText).then(() => {
                showToast("📢 Postcard Score copied to clipboard!");
            }).catch(err => console.error("Clipboard error:", err));
        };
    }

    const openFullBtn = document.getElementById('btn-map-pc-open-full');
    if (openFullBtn) {
        openFullBtn.onclick = () => {
            closeMapPostcardOverlay();
            const mapModal = document.getElementById('world-map-modal');
            if (mapModal) mapModal.classList.remove('active');
            startGame(challenge);
            history.replaceState(null, "", `?challenge=${challenge.puzzle_number}`);
        };
    }

    modal.classList.add('active');
    sendTelemetryEvent('click_map_pin');
}

function closeMapPostcardOverlay() {
    const modal = document.getElementById('map-postcard-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function updateWorldMapBadges() {
    try {
        const solvedSet = getSolvedPuzzlesList();
        const approved = getApprovedChallenges();
        const solvedCount = approved.filter(c => solvedSet.has(padPuzzleNumber(c.puzzle_number))).length;
        const totalAvailable = approved.length;

        const badgeGame = document.getElementById('world-map-pin-count');
        const badgeVic = document.getElementById('world-map-pin-count-victory');
        [badgeGame, badgeVic].forEach(el => {
            if (!el) return;
            el.innerText = solvedCount.toString();
            el.classList.toggle('hidden', solvedCount === 0);
        });

        const tabPillStats = document.getElementById('tab-map-count-pill');
        const tabPillMap = document.getElementById('world-map-tab-pill');
        if (tabPillStats) tabPillStats.innerText = solvedCount.toString();
        if (tabPillMap) tabPillMap.innerText = solvedCount.toString();

        const statsCtaBadge = document.getElementById('stats-map-cta-badge');
        if (statsCtaBadge) {
            statsCtaBadge.innerText = `${solvedCount} Pinned ➔`;
        }

        const solvedBadge = document.getElementById('world-map-solved-badge');
        if (solvedBadge) {
            solvedBadge.innerText = `📍 ${solvedCount} / ${totalAvailable} Solved`;
        }

        const completedCountLabel = document.getElementById('map-completed-count-label');
        if (completedCountLabel) {
            completedCountLabel.innerText = `${solvedCount} Completed`;
        }
    } catch (e) {
        console.warn("Could not update world map badges:", e);
    }
}

function openWorldMapModal() {
    const worldMapModal = document.getElementById('world-map-modal');
    const statsSelectModal = document.getElementById('stats-select-modal');
    if (!worldMapModal) return;

    if (statsSelectModal) {
        statsSelectModal.classList.remove('active');
    }

    if (!worldMapState.initialized) {
        renderBaseWorldMapSVG();
        worldMapState.initialized = true;
    }

    renderSolvedMapPinsAndList();
    applyWorldMapTransform();
    worldMapModal.classList.add('active');

    sendTelemetryEvent('click_world_map');
    if (typeof gtag !== 'undefined') {
        gtag('event', 'page_view', {
            page_title: 'World Travel Map',
            page_path: '/world-map'
        });
    }
}

function initWorldMapFeature() {
    const worldMapModal = document.getElementById('world-map-modal');
    const statsSelectModal = document.getElementById('stats-select-modal');
    const mapPostcardModal = document.getElementById('map-postcard-modal');

    const btnWorldMap = document.getElementById('btn-world-map');
    const btnWorldMapVic = document.getElementById('btn-world-map-victory');
    const btnCloseWorldMap = document.getElementById('btn-close-world-map');

    if (btnWorldMap) btnWorldMap.onclick = openWorldMapModal;
    if (btnWorldMapVic) btnWorldMapVic.onclick = openWorldMapModal;

    if (btnCloseWorldMap) {
        btnCloseWorldMap.onclick = () => {
            hideWorldMapPinTooltip();
            if (worldMapModal) worldMapModal.classList.remove('active');
        };
    }

    if (worldMapModal) {
        worldMapModal.onclick = (e) => {
            if (e.target === worldMapModal) {
                hideWorldMapPinTooltip();
                worldMapModal.classList.remove('active');
            }
        };
    }

    // Cross-modal Tab & CTA navigation between World Map and Global Stats
    const switchFromMapToStats = () => {
        hideWorldMapPinTooltip();
        if (worldMapModal) worldMapModal.classList.remove('active');
        if (statsSelectModal) {
            statsSelectModal.classList.add('active');
            openStatsSelectModal();
        }
    };

    const tabStatsToMap = document.getElementById('tab-stats-to-map');
    const btnOpenMapFromStats = document.getElementById('btn-open-map-from-stats');
    const tabMapToStats = document.getElementById('tab-map-to-stats');
    const btnMapToStats = document.getElementById('btn-map-to-stats');

    if (tabStatsToMap) tabStatsToMap.onclick = openWorldMapModal;
    if (btnOpenMapFromStats) btnOpenMapFromStats.onclick = openWorldMapModal;
    if (tabMapToStats) tabMapToStats.onclick = switchFromMapToStats;
    if (btnMapToStats) btnMapToStats.onclick = switchFromMapToStats;

    // 1-Click Postcard Overlay Close & Reviews Toggle
    const btnCloseMapPostcard = document.getElementById('btn-close-map-postcard');
    if (btnCloseMapPostcard) {
        btnCloseMapPostcard.onclick = closeMapPostcardOverlay;
    }
    if (mapPostcardModal) {
        mapPostcardModal.onclick = (e) => {
            if (e.target === mapPostcardModal) {
                closeMapPostcardOverlay();
            }
        };
    }

    const btnMapPcToggleReviews = document.getElementById('btn-map-pc-toggle-reviews');
    const mapPcReviewsBox = document.getElementById('map-pc-reviews-box');
    if (btnMapPcToggleReviews && mapPcReviewsBox) {
        btnMapPcToggleReviews.onclick = () => {
            const isHidden = mapPcReviewsBox.classList.toggle('hidden');
            btnMapPcToggleReviews.innerText = isHidden ? '1-Star Reviews ▼' : '1-Star Reviews ▲';
        };
    }

    // Escape key closes topmost overlay first (#map-postcard-modal -> #world-map-modal)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (mapPostcardModal && mapPostcardModal.classList.contains('active')) {
                closeMapPostcardOverlay();
                return;
            }
            if (worldMapModal && worldMapModal.classList.contains('active')) {
                hideWorldMapPinTooltip();
                worldMapModal.classList.remove('active');
            }
        }
    });

    // Region Quick-Jump Pills
    document.querySelectorAll('#world-map-region-pills .map-region-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            hideWorldMapPinTooltip();
            setWorldMapRegion(btn.dataset.region);
        });
    });

    // Map Zoom Controls (+ / - / Reset)
    const btnZoomIn = document.getElementById('map-zoom-in');
    const btnZoomOut = document.getElementById('map-zoom-out');
    const btnZoomReset = document.getElementById('map-zoom-reset');
    if (btnZoomIn) btnZoomIn.onclick = () => zoomWorldMapBy(1.45);
    if (btnZoomOut) btnZoomOut.onclick = () => zoomWorldMapBy(1 / 1.45);
    if (btnZoomReset) btnZoomReset.onclick = () => setWorldMapRegion('world');

    // Interactive Mouse Wheel Zoom & Drag-to-Pan on #world-map-viewport
    const viewport = document.getElementById('world-map-viewport');
    const svg = document.getElementById('world-map-svg');
    if (viewport && svg) {
        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            hideWorldMapPinTooltip();
            const rect = svg.getBoundingClientRect();
            const svgX = ((e.clientX - rect.left) / rect.width) * WORLD_MAP_WIDTH;
            const svgY = ((e.clientY - rect.top) / rect.height) * WORLD_MAP_HEIGHT;
            const factor = e.deltaY < 0 ? 1.25 : (1 / 1.25);
            zoomWorldMapBy(factor, svgX, svgY);
        }, { passive: false });

        const startDrag = (clientX, clientY) => {
            worldMapState.isDragging = true;
            worldMapState.dragMoved = false;
            worldMapState.dragStartX = clientX;
            worldMapState.dragStartY = clientY;
            worldMapState.startTx = worldMapState.tx;
            worldMapState.startTy = worldMapState.ty;
            viewport.classList.add('dragging');
        };

        const moveDrag = (clientX, clientY) => {
            if (!worldMapState.isDragging) return;
            const rect = svg.getBoundingClientRect();
            if (!rect.width || !rect.height) return;
            const dxPx = clientX - worldMapState.dragStartX;
            const dyPx = clientY - worldMapState.dragStartY;
            if (Math.abs(dxPx) > 4 || Math.abs(dyPx) > 4) {
                worldMapState.dragMoved = true;
                hideWorldMapPinTooltip();
            }
            const dxSvg = (dxPx / rect.width) * WORLD_MAP_WIDTH;
            const dySvg = (dyPx / rect.height) * WORLD_MAP_HEIGHT;
            worldMapState.tx = worldMapState.startTx + dxSvg;
            worldMapState.ty = worldMapState.startTy + dySvg;
            applyWorldMapTransform();
        };

        const endDrag = () => {
            worldMapState.isDragging = false;
            viewport.classList.remove('dragging');
        };

        viewport.addEventListener('mousedown', (e) => {
            if (e.target.closest('.map-ctrl-btn')) return;
            startDrag(e.clientX, e.clientY);
        });
        window.addEventListener('mousemove', (e) => moveDrag(e.clientX, e.clientY));
        window.addEventListener('mouseup', endDrag);

        viewport.addEventListener('touchstart', (e) => {
            if (e.target.closest('.map-ctrl-btn')) return;
            if (e.touches.length === 1) {
                startDrag(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });
        viewport.addEventListener('touchmove', (e) => {
            if (worldMapState.isDragging && e.touches.length === 1) {
                moveDrag(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });
        viewport.addEventListener('touchend', endDrag);
    }
}
