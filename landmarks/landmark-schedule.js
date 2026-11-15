/**
 * PunFiction Landmark Field Guides — Daily Live Release Sync
 * Synchronizes landmark availability 1:1 with 1-Star Travel Reviews daily challenges
 * (New puzzle + landmark unlock together daily at 2:00 AM America/Los_Angeles, epoch 2026-07-04).
 */
(function () {
    var MAX_LANDMARK_PUZZLE = 181;
    var MANIFEST = [[1, "001", "challenge-001-eiffel-tower.html", "Eiffel Tower"], [2, "002", "challenge-002-great-wall-of-china.html", "Great Wall of China"], [3, "003", "challenge-003-taj-mahal.html", "Taj Mahal"], [4, "004", "challenge-004-pyramids-of-giza.html", "Pyramids of Giza"], [5, "005", "challenge-005-stonehenge.html", "Stonehenge"], [6, "006", "challenge-006-sagrada-familia.html", "Sagrada Família"], [7, "007", "challenge-007-golden-gate-bridge.html", "Golden Gate Bridge"], [8, "008", "challenge-008-petra.html", "Petra"], [9, "009", "challenge-009-chichen-itza.html", "Chichen Itza"], [10, "010", "challenge-010-angkor-wat.html", "Angkor Wat"], [11, "011", "challenge-011-christ-the-redeemer.html", "Christ the Redeemer"], [12, "012", "challenge-012-colosseum.html", "Colosseum"], [13, "013", "challenge-013-panama-canal.html", "Panama Canal"], [14, "014", "challenge-014-big-ben.html", "Big Ben"], [15, "015", "challenge-015-great-barrier-reef.html", "Great Barrier Reef"], [16, "016", "challenge-016-yellowstone-national-park.html", "Yellowstone National Park"], [17, "017", "challenge-017-leaning-tower-of-pisa.html", "Leaning Tower of Pisa"], [18, "018", "challenge-018-empire-state-building.html", "Empire State Building"], [19, "019", "challenge-019-times-square.html", "Times Square"], [20, "020", "challenge-020-burj-khalifa.html", "Burj Khalifa"], [21, "021", "challenge-021-tower-bridge.html", "Tower Bridge"], [22, "022", "challenge-022-st-peter-s-basilica.html", "St. Peter's Basilica"], [23, "023", "challenge-023-pantheon.html", "Pantheon"], [24, "024", "challenge-024-grand-canal.html", "Grand Canal"], [25, "025", "challenge-025-spanish-steps.html", "Spanish Steps"], [26, "026", "challenge-026-loch-ness.html", "Loch Ness"], [27, "027", "challenge-027-alcatraz-island.html", "Alcatraz Island"], [28, "028", "challenge-028-machu-picchu.html", "Machu Picchu"], [29, "029", "challenge-029-tower-of-london.html", "Tower of London"], [30, "030", "challenge-030-edinburgh-castle.html", "Edinburgh Castle"], [31, "031", "challenge-031-black-forest.html", "Black Forest"], [32, "032", "challenge-032-matterhorn.html", "Matterhorn"], [33, "033", "challenge-033-cliffs-of-moher.html", "Cliffs of Moher"], [34, "034", "challenge-034-space-needle.html", "Space Needle"], [35, "035", "challenge-035-giant-s-causeway.html", "Giant's Causeway"], [36, "036", "challenge-036-la-rambla.html", "La Rambla"], [37, "037", "challenge-037-santorini.html", "Santorini"], [38, "038", "challenge-038-notre-dame-cathedral.html", "Notre-Dame Cathedral"], [39, "039", "challenge-039-atomium.html", "Atomium"], [40, "040", "challenge-040-mont-saint-michel.html", "Mont Saint-Michel"], [41, "041", "challenge-041-roman-forum.html", "Roman Forum"], [42, "042", "challenge-042-blarney-castle.html", "Blarney Castle"], [43, "043", "challenge-043-dublin-castle.html", "Dublin Castle"], [44, "044", "challenge-044-st-basil-s-cathedral.html", "St. Basil's Cathedral"], [45, "045", "challenge-045-mesa-verde-national-park.html", "Mesa Verde National Park"], [46, "046", "challenge-046-neuschwanstein-castle.html", "Neuschwanstein Castle"], [47, "047", "challenge-047-grand-canyon.html", "Grand Canyon"], [48, "048", "challenge-048-pompeii.html", "Pompeii"], [49, "049", "challenge-049-buckingham-palace.html", "Buckingham Palace"], [50, "050", "challenge-050-alhambra.html", "Alhambra"], [51, "051", "challenge-051-keukenhof.html", "Keukenhof"], [52, "052", "challenge-052-lake-louise.html", "Lake Louise"], [53, "053", "challenge-053-the-shard.html", "The Shard"], [54, "054", "challenge-054-parthenon.html", "Parthenon"], [55, "055", "challenge-055-roman-baths.html", "Roman Baths"], [56, "056", "challenge-056-mount-st-helens.html", "Mount St. Helens"], [57, "057", "challenge-057-brandenburg-gate.html", "Brandenburg Gate"], [58, "058", "challenge-058-reichstag-building.html", "Reichstag Building"], [59, "059", "challenge-059-cologne-cathedral.html", "Cologne Cathedral"], [60, "060", "challenge-060-palace-of-knossos.html", "Palace of Knossos"], [61, "061", "challenge-061-gateway-arch.html", "Gateway Arch"], [62, "062", "challenge-062-eiffel-tower.html", "Eiffel Tower"], [63, "063", "challenge-063-great-wall-of-china.html", "Great Wall of China"], [64, "064", "challenge-064-taj-mahal.html", "Taj Mahal"], [65, "065", "challenge-065-panama-canal.html", "Panama Canal"], [66, "066", "challenge-066-times-square.html", "Times Square"], [67, "067", "challenge-067-big-ben.html", "Big Ben"], [68, "068", "challenge-068-colosseum.html", "Colosseum"], [69, "069", "challenge-069-leaning-tower-of-pisa.html", "Leaning Tower of Pisa"], [70, "070", "challenge-070-eiffel-tower.html", "Eiffel Tower"], [71, "071", "challenge-071-tower-bridge.html", "Tower Bridge"], [72, "072", "challenge-072-eiffel-tower.html", "Eiffel Tower"], [73, "073", "challenge-073-grand-canyon.html", "Grand Canyon"], [74, "074", "challenge-074-big-ben.html", "Big Ben"], [75, "075", "challenge-075-yellowstone-national-park.html", "Yellowstone National Park"], [76, "076", "challenge-076-keukenhof.html", "Keukenhof"], [77, "077", "challenge-077-st-basil-s-cathedral.html", "St. Basil's Cathedral"], [78, "078", "challenge-078-black-forest.html", "Black Forest"], [79, "079", "challenge-079-cliffs-of-moher.html", "Cliffs of Moher"], [80, "080", "challenge-080-dublin-castle.html", "Dublin Castle"], [81, "081", "challenge-081-giant-s-causeway.html", "Giant's Causeway"], [82, "082", "challenge-082-alcatraz-island.html", "Alcatraz Island"], [83, "083", "challenge-083-machu-picchu.html", "Machu Picchu"], [84, "084", "challenge-084-chichen-itza.html", "Chichen Itza"], [85, "085", "challenge-085-palace-of-versailles.html", "Palace of Versailles"], [86, "086", "challenge-086-tikal.html", "Tikal"], [87, "087", "challenge-087-milan-cathedral.html", "Milan Cathedral"], [88, "088", "challenge-088-meteora.html", "Meteora"], [89, "089", "challenge-089-grand-place.html", "Grand Place"], [90, "090", "challenge-090-kennedy-space-center.html", "Kennedy Space Center"], [91, "091", "challenge-091-everglades-national-park.html", "Everglades National Park"], [92, "092", "challenge-092-rocky-mountains.html", "Rocky Mountains"], [93, "093", "challenge-093-great-blue-hole.html", "Great Blue Hole"], [94, "094", "challenge-094-hollywood-sign.html", "Hollywood Sign"], [95, "095", "challenge-095-alcazar-of-seville.html", "Alcázar of Seville"], [96, "096", "challenge-096-amazon-rainforest.html", "Amazon Rainforest"], [97, "097", "challenge-097-copacabana-beach.html", "Copacabana Beach"], [98, "098", "challenge-098-nazca-lines.html", "Nazca Lines"], [99, "099", "challenge-099-brooklyn-bridge.html", "Brooklyn Bridge"], [100, "100", "challenge-100-galapagos-islands.html", "Galapagos Islands"], [101, "101", "challenge-101-victoria-falls.html", "Victoria Falls"], [102, "102", "challenge-102-valley-of-the-kings.html", "Valley of the Kings"], [103, "103", "challenge-103-gamla-stan.html", "Gamla Stan"], [104, "104", "challenge-104-atacama-desert.html", "Atacama Desert"], [105, "105", "challenge-105-great-wall-of-china.html", "Great Wall of China"], [106, "106", "challenge-106-stonehenge.html", "Stonehenge"], [107, "107", "challenge-107-mount-fuji.html", "Mount Fuji"], [108, "108", "challenge-108-yellowstone-national-park.html", "Yellowstone National Park"], [109, "109", "challenge-109-notre-dame-cathedral.html", "Notre-Dame Cathedral"], [110, "110", "challenge-110-grand-canal.html", "Grand Canal"], [111, "111", "challenge-111-pompeii.html", "Pompeii"], [112, "112", "challenge-112-machu-picchu.html", "Machu Picchu"], [113, "113", "challenge-113-empire-state-building.html", "Empire State Building"], [114, "114", "challenge-114-petra.html", "Petra"], [115, "115", "challenge-115-times-square.html", "Times Square"], [116, "116", "challenge-116-louvre-museum.html", "Louvre Museum"], [117, "117", "challenge-117-mont-saint-michel.html", "Mont Saint-Michel"], [118, "118", "challenge-118-alcatraz-island.html", "Alcatraz Island"], [119, "119", "challenge-119-spanish-steps.html", "Spanish Steps"], [120, "120", "challenge-120-spanish-steps.html", "Spanish Steps"], [121, "121", "challenge-121-amalfi-coast.html", "Amalfi Coast"], [122, "122", "challenge-122-buckingham-palace.html", "Buckingham Palace"], [123, "123", "challenge-123-dubrovnik-old-town.html", "Dubrovnik Old Town"], [124, "124", "challenge-124-blue-lagoon.html", "Blue Lagoon"], [125, "125", "challenge-125-shilin-stone-forest.html", "Shilin Stone Forest"], [126, "126", "challenge-126-meiji-jingu-shrine.html", "Meiji Jingu Shrine"], [127, "127", "challenge-127-prague-castle.html", "Prague Castle"], [128, "128", "challenge-128-blyde-river-canyon.html", "Blyde River Canyon"], [129, "129", "challenge-129-casa-rosada.html", "Casa Rosada"], [130, "130", "challenge-130-tulum-ruins.html", "Tulum Ruins"], [131, "131", "challenge-131-lord-howe-island-group.html", "Lord Howe Island Group"], [132, "132", "challenge-132-djemaa-el-fna.html", "Djemaa el-Fna"], [133, "133", "challenge-133-charles-bridge.html", "Charles Bridge"], [134, "134", "challenge-134-parliament-hill.html", "Parliament Hill"], [135, "135", "challenge-135-elephanta-caves.html", "Elephanta Caves"], [136, "136", "challenge-136-walls-of-dubrovnik.html", "Walls of Dubrovnik"], [137, "137", "challenge-137-la-boca-caminito.html", "La Boca (Caminito)"], [138, "138", "challenge-138-pinnacles-desert.html", "Pinnacles Desert"], [139, "139", "challenge-139-mount-sinai.html", "Mount Sinai"], [140, "140", "challenge-140-khan-el-khalili.html", "Khan el-Khalili"], [141, "141", "challenge-141-the-strip-las-vegas.html", "The Strip, Las Vegas"], [142, "142", "challenge-142-senso-ji-temple.html", "Senso-ji Temple"], [143, "143", "challenge-143-the-great-buddha-of-kamakura.html", "The Great Buddha of Kamakura"], [144, "144", "challenge-144-quebec-city-old-town.html", "Quebec City Old Town"], [145, "145", "challenge-145-olduvai-gorge.html", "Olduvai Gorge"], [146, "146", "challenge-146-osaka-castle.html", "Osaka Castle"], [147, "147", "challenge-147-the-blue-lagoon.html", "The Blue Lagoon"], [148, "148", "challenge-148-hallstatt.html", "Hallstatt"], [149, "149", "challenge-149-plitvice-lakes-national-park.html", "Plitvice Lakes National Park"], [150, "150", "challenge-150-jemaa-el-fnaa.html", "Jemaa el-Fnaa"], [151, "151", "challenge-151-shwedagon-pagoda.html", "Shwedagon Pagoda"], [152, "152", "challenge-152-mount-kenya.html", "Mount Kenya"], [153, "153", "challenge-153-cerro-monserrate.html", "Cerro Monserrate"], [154, "154", "challenge-154-the-pitons.html", "The Pitons"], [155, "155", "challenge-155-arenal-volcano.html", "Arenal Volcano"], [156, "156", "challenge-156-registan-square.html", "Registan Square"], [157, "157", "challenge-157-fisherman-s-bastion.html", "Fisherman's Bastion"], [158, "158", "challenge-158-geirangerfjord.html", "Geirangerfjord"], [159, "159", "challenge-159-prague-astronomical-clock.html", "Prague Astronomical Clock"], [160, "160", "challenge-160-tiger-s-nest-monastery-paro-taktsang.html", "Tiger's Nest Monastery (Paro Taktsang)"], [161, "161", "challenge-161-lake-titicaca.html", "Lake Titicaca"], [162, "162", "challenge-162-dunn-s-river-falls.html", "Dunn's River Falls"], [163, "163", "challenge-163-boracay-island.html", "Boracay Island"], [164, "164", "challenge-164-haedong-yonggungsa-temple.html", "Haedong Yonggungsa Temple"], [165, "165", "challenge-165-babylon.html", "Babylon"], [166, "166", "challenge-166-fish-river-canyon.html", "Fish River Canyon"], [167, "167", "challenge-167-mount-rainier.html", "Mount Rainier"], [168, "168", "challenge-168-deception-island.html", "Deception Island"], [169, "169", "challenge-169-jeita-grotto.html", "Jeita Grotto"], [170, "170", "challenge-170-gros-morne-national-park.html", "Gros Morne National Park"], [171, "171", "challenge-171-land-s-end-arch.html", "Land's End Arch"], [172, "172", "challenge-172-cinque-terre.html", "Cinque Terre"], [173, "173", "challenge-173-pena-palace.html", "Pena Palace"], [174, "174", "challenge-174-blue-mosque.html", "Blue Mosque"], [175, "175", "challenge-175-willis-tower.html", "Willis Tower"], [176, "176", "challenge-176-burj-al-arab-jumeirah.html", "Burj Al Arab Jumeirah"], [177, "177", "challenge-177-jigokudani-monkey-park.html", "Jigokudani Monkey Park"], [178, "178", "challenge-178-the-london-eye.html", "The London Eye"], [179, "179", "challenge-179-great-zimbabwe-ruins.html", "Great Zimbabwe Ruins"], [180, "180", "challenge-180-nara-park.html", "Nara Park"], [181, "181", "challenge-181-westminster-abbey.html", "Westminster Abbey"]];

    function getDaysElapsedSinceStart() {
        try {
            var now = new Date();
            var parts = new Intl.DateTimeFormat("en-US", {
                timeZone: "America/Los_Angeles",
                year: "numeric",
                month: "numeric",
                day: "numeric",
                hour: "numeric",
                minute: "numeric",
                second: "numeric",
                hour12: false
            }).formatToParts(now);
            var val = function (t) {
                return parseInt(parts.find(function (p) { return p.type === t; }).value, 10);
            };
            var nowPTUtc = Date.UTC(
                val("year"),
                val("month") - 1,
                val("day"),
                val("hour") % 24,
                val("minute"),
                val("second")
            );
            var startPTUtc = Date.UTC(2026, 6, 4, 2, 0, 0);
            return Math.max(0, Math.floor((nowPTUtc - startPTUtc) / 86400000));
        } catch (e) {
            var start = new Date("2026-07-04T02:00:00-07:00");
            return Math.max(0, Math.floor((Date.now() - start.getTime()) / 86400000));
        }
    }

    function pad3(n) {
        return String(n).padStart(3, "0");
    }

    var liveCount = Math.min(MAX_LANDMARK_PUZZLE, Math.max(1, getDaysElapsedSinceStart() + 1));

    // 1. Directory Index Hub (/travelreviews/landmarks/index.html)
    var hubMain = document.getElementById("landmarks-hub-main");
    if (hubMain) {
        var cards = hubMain.querySelectorAll(".related-card[data-puzzle]");
        for (var c = 0; c < cards.length; c++) {
            var card = cards[c];
            var pnum = parseInt(card.getAttribute("data-puzzle"), 10);
            var isLive = pnum <= liveCount;
            card.classList.toggle("future-locked", !isLive);
            var todayBadge = card.querySelector(".card-today-pill");
            if (pnum === liveCount) {
                if (!todayBadge) {
                    var badgeRow = card.querySelector(".card-top-row");
                    if (badgeRow) {
                        var pill = document.createElement("span");
                        pill.className = "badge badge-today card-today-pill";
                        pill.style.fontSize = "0.65rem";
                        pill.style.padding = "2px 6px";
                        pill.textContent = "Today";
                        badgeRow.appendChild(pill);
                    }
                }
            } else if (todayBadge) {
                todayBadge.remove();
            }
        }

        var sections = hubMain.querySelectorAll(".region-section");
        for (var s = 0; s < sections.length; s++) {
            var sec = sections[s];
            var secCards = sec.querySelectorAll(".related-card[data-puzzle]");
            var visCount = 0;
            for (var k = 0; k < secCards.length; k++) {
                if (!secCards[k].classList.contains("future-locked")) visCount++;
            }
            sec.style.display = visCount > 0 ? "" : "none";
        }
        return;
    }

    // 2. Individual Landmark Field Guide Page
    var pagePuzzleAttr = document.documentElement.getAttribute("data-puzzle-num");
    if (!pagePuzzleAttr) return;
    var thisPuzzleNum = parseInt(pagePuzzleAttr, 10);

    if (thisPuzzleNum > liveCount) {
        document.documentElement.classList.add("landmark-locked");
        document.title = "Challenge #" + pad3(thisPuzzleNum) + " \u2014 Unlocks Soon | PunFiction";
        return;
    } else {
        document.documentElement.classList.remove("landmark-locked");
    }

    // Sync Prev / Next buttons so navigation wraps cleanly within 1..liveCount
    var liveItems = [];
    for (var m = 0; m < MANIFEST.length; m++) {
        if (MANIFEST[m][0] <= liveCount) liveItems.push(MANIFEST[m]);
    }
    var currIdx = -1;
    for (var idx = 0; idx < liveItems.length; idx++) {
        if (liveItems[idx][0] === thisPuzzleNum) {
            currIdx = idx;
            break;
        }
    }
    if (currIdx !== -1 && liveItems.length > 0) {
        var prevItem = currIdx > 0 ? liveItems[currIdx - 1] : liveItems[liveItems.length - 1];
        var nextItem = currIdx + 1 < liveItems.length ? liveItems[currIdx + 1] : liveItems[0];
        var prevEl = document.getElementById("nav-prev-landmark");
        var nextEl = document.getElementById("nav-next-landmark");
        if (prevEl) {
            prevEl.href = "./" + prevItem[2];
            prevEl.textContent = "\u2190 Prev: #" + prevItem[1] + " " + prevItem[3];
        }
        if (nextEl) {
            nextEl.href = "./" + nextItem[2];
            nextEl.textContent = "Next: #" + nextItem[1] + " " + nextItem[3] + " \u2192";
        }
    }

    // Filter related region cards so only live landmarks (<= liveCount) appear (max 6)
    var relGrid = document.getElementById("related-region-grid");
    if (relGrid) {
        var relCards = relGrid.querySelectorAll(".related-card[data-puzzle]");
        var shown = 0;
        for (var rc = 0; rc < relCards.length; rc++) {
            var rcNum = parseInt(relCards[rc].getAttribute("data-puzzle"), 10);
            if (rcNum <= liveCount && shown < 6) {
                relCards[rc].classList.remove("future-locked", "peer-overflow");
                shown++;
            } else {
                relCards[rc].classList.add(rcNum > liveCount ? "future-locked" : "peer-overflow");
            }
        }
    }
})();
