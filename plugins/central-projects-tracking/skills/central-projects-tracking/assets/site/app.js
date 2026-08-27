(function () {
  "use strict";

  const snapshot = window.CENTRAL_PROJECTS_SNAPSHOT;
  const root = document.getElementById("main-content");
  const drawerRoot = document.getElementById("drawer-root");
  const liveRegion = document.getElementById("live-region");
  const views = new Set(["brief", "portfolio", "activity", "system"]);
  const stages = ["Unknown", "Idea", "Foundation", "Build", "Integration", "Live"];
  const state = { view: "brief", query: "", filter: "all", selectedId: null };
  let returnFocus = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function append(parent, ...children) {
    children.filter(Boolean).forEach((child) => parent.appendChild(child));
    return parent;
  }

  function button(label, className, action) {
    const node = element("button", className, label);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
  }

  function parseDay(value) {
    return value ? new Date(value.length === 10 ? value + "T00:00:00Z" : value) : null;
  }

  function formatDate(value, long) {
    const date = parseDay(value);
    if (!date || Number.isNaN(date.getTime())) return "No evidence";
    return new Intl.DateTimeFormat("en", {
      timeZone: "UTC",
      day: "2-digit",
      month: long ? "long" : "short",
      year: long ? "numeric" : undefined,
      weekday: long ? "long" : undefined,
      hour: value && value.includes("T") ? "2-digit" : undefined,
      minute: value && value.includes("T") ? "2-digit" : undefined,
      hour12: false,
    }).format(date).replace(",", " ·");
  }

  function countNoun(count, singular, plural) {
    return count + " " + (count === 1 ? singular : (plural || singular + "s"));
  }

  function repositoryOf(project) {
    return project.repository || {};
  }

  function statusNode(tone, label) {
    const node = element("span", "status status-" + (tone || "neutral"));
    const dot = element("i");
    dot.setAttribute("aria-hidden", "true");
    return append(node, dot, document.createTextNode(label || "Unknown"));
  }

  function gitLabel(project) {
    const repository = repositoryOf(project);
    if (!project.present) return "Not detected";
    if (repository.state === "unavailable") return "Unavailable";
    if (!repository.changeCount) return repository.state === "unborn" ? "No commits" : "Clean";
    return countNoun(repository.changeCount, "local change");
  }

  function branchLabel(project) {
    const repository = repositoryOf(project);
    let label = repository.branchRedacted ? "Withheld" : repository.branch;
    if (!label) label = repository.state === "unborn" ? "No commits" : "Detached or unavailable";
    if (repository.ahead) label += " · ahead " + repository.ahead;
    if (repository.behind) label += " · behind " + repository.behind;
    return label;
  }

  function activityLabel(project) {
    const activity = project.lastActivity || {};
    if (!activity.on) return "No evidence";
    return formatDate(activity.on, false) + (activity.kind === "evidence" ? " evidence" : "");
  }

  function projectRow(project, rank) {
    const row = element("button", "project-row");
    row.type = "button";
    row.setAttribute("aria-label", "Open " + project.name + " project details");
    row.addEventListener("click", (event) => openProject(project.id, event.currentTarget));
    const rankNode = element("span", "row-rank", String(rank).padStart(2, "0"));
    const projectNode = append(element("span", "row-project"), element("strong", "", project.name), element("small", "", project.summary));
    const stageNode = element("span", "row-stage");
    const track = element("i");
    const fill = element("b");
    const stageIndex = Math.max(0, stages.indexOf(project.stage));
    fill.style.width = Math.round(((stageIndex + 1) / stages.length) * 100) + "%";
    append(track, fill);
    append(stageNode, element("span", "", project.stage), track);
    const healthNode = append(element("span", "row-health"), statusNode(project.tone, project.health));
    const gitNode = append(element("span", "row-git"), element("strong", "", gitLabel(project)), element("small", "", branchLabel(project)));
    const activityNode = append(element("span", "row-activity"), element("strong", "", activityLabel(project)), element("small", "", "Last evidence"));
    return append(row, rankNode, projectNode, stageNode, healthNode, gitNode, activityNode, element("span", "row-arrow", "↗"));
  }

  function projectTable(projects) {
    const wrapper = element("div", "project-table");
    const head = element("div", "table-head");
    head.setAttribute("aria-hidden", "true");
    ["No.", "Project / signal", "Stage", "Health", "Git state", "Activity", ""].forEach((label) => head.appendChild(element("span", "", label)));
    wrapper.appendChild(head);
    projects.forEach((project, index) => wrapper.appendChild(projectRow(project, index + 1)));
    if (!projects.length) {
      const empty = append(element("div", "empty-state"), element("strong", "", "No matching projects."), element("span", "", "Clear the search or choose a different signal filter."));
      wrapper.appendChild(empty);
    }
    return wrapper;
  }

  function metric(index, value, label, note, attention) {
    const article = element("article", attention ? "metric-attention" : "");
    return append(article, element("span", "metric-index", String(index).padStart(2, "0")), element("strong", "", String(value).padStart(2, "0")), element("p", "", label), element("small", "", note));
  }

  function panelHeading(kicker, title, action) {
    const heading = element("div", "panel-heading");
    const copy = append(element("div"), element("p", "kicker", kicker), element("h2", "", title));
    return append(heading, copy, action);
  }

  function briefSignalPanel(id, kicker, title, items, emptyText, marker) {
    const panel = element("section", "panel brief-signal " + id + "-signal");
    const headingId = "brief-" + id + "-title";
    panel.setAttribute("aria-labelledby", headingId);

    const titleNode = element("h2", "", title);
    titleNode.id = headingId;
    const countLabel = items.length === 1 ? "1 item" : items.length + " items";
    append(panel,
      append(element("div", "panel-heading compact"),
        append(element("div"), element("p", "kicker", kicker), titleNode),
        element("span", "signal-count", countLabel)));

    if (!items.length) {
      panel.appendChild(element("p", "signal-empty", emptyText));
      return panel;
    }

    const list = element(marker === "decision" ? "ol" : "ul", "signal-list");
    items.forEach((item, index) => {
      const markerNode = element(
        "span",
        "signal-marker",
        marker === "decision" ? String(index + 1).padStart(2, "0") : "!"
      );
      markerNode.setAttribute("aria-hidden", "true");
      append(list, append(element("li"), markerNode, element("p", "", item)));
    });
    panel.appendChild(list);
    return panel;
  }

  function renderBrief() {
    const projects = snapshot.projects;
    const present = projects.filter((project) => project.present);
    const localWork = present.filter((project) => repositoryOf(project).changeCount > 0);
    const attention = present.filter((project) => project.attention);
    const clean = present.filter((project) => repositoryOf(project).state === "clean");
    const focusIds = snapshot.brief.focusProjectIds || [];
    const focus = focusIds.map((id) => projects.find((project) => project.id === id)).filter(Boolean);
    const readyIds = snapshot.brief.readyProjectIds || [];
    const ready = readyIds.map((id) => projects.find((project) => project.id === id)).filter(Boolean);
    const view = element("section", "view brief-view");

    const hero = element("section", "hero");
    const heroCopy = element("div", "hero-copy");
    append(heroCopy,
      element("p", "kicker", "Evidence portfolio · " + formatDate(snapshot.generatedAt, true)),
      element("h1", "", present.length + " projects. What needs attention, what moved, and what happens next."),
      element("p", "hero-note", "A safe, point-in-time reading of local Git state and approved project evidence. It is not live telemetry, a completion score, or proof of deployment health."),
      append(element("div", "hero-actions"),
        button("Scan the portfolio  ↗", "button-primary", () => goToView("portfolio")),
        button("Review activity", "button-quiet", () => goToView("activity"))));
    const metrics = element("div", "metric-grid");
    metrics.setAttribute("aria-label", "Portfolio snapshot");
    append(metrics,
      metric(1, present.length, "Projects detected", snapshot.scopeLabel),
      metric(2, localWork.length, "Local work in progress", "Path-free Git counts"),
      metric(3, attention.length, "Need a decision", "Blocked, gated, or uncertain", true),
      metric(4, clean.length, "Clean worktrees", clean.length ? clean.map((project) => project.name).join(" · ") : "None"));
    append(hero, heroCopy, metrics);
    view.appendChild(hero);

    const grid = element("section", "control-grid");
    const focusPanel = element("div", "panel focus-panel");
    append(focusPanel,
      panelHeading("Attention queue", "Today’s architect brief", button("All " + present.length + " projects ↗", "text-action", () => goToView("portfolio"))),
      projectTable(focus.length ? focus : attention.slice(0, 5)));

    const rail = element("aside", "brief-rail");
    rail.setAttribute("aria-label", "Construction and source status");
    const stagePanel = element("section", "panel stages-panel");
    stagePanel.appendChild(panelHeading("Construction map", "Delivery stages"));
    const stageList = element("ol", "stage-list");
    stages.forEach((stage, index) => {
      const count = present.filter((project) => project.stage === stage).length;
      const track = element("i");
      const fill = element("b");
      fill.style.width = Math.min(100, count * 22) + "%";
      append(track, fill);
      append(stageList, append(element("li"), element("span", "", String(index + 1).padStart(2, "0")), element("strong", "", stage), track, element("em", "", count)));
    });

    const pulsePanel = element("section", "panel pulse-panel");
    pulsePanel.appendChild(panelHeading("Source integrity", "Portfolio pulse"));
    const pulse = element("ul", "pulse-list");
    const pulseItem = (good, title, note) => append(element("li"), element("span", "pulse-dot" + (good ? " good" : "")), append(element("span"), element("strong", "", title), element("small", "", note)));
    append(pulse,
      pulseItem(true, "Validated snapshot", snapshot.coverage.completeProjectCount + " complete source" + (snapshot.coverage.completeProjectCount === 1 ? "" : "s")),
      pulseItem(false, "Runtime telemetry", "Not connected"),
      pulseItem(true, "Safe-data boundary", "Secrets, raw paths, and diffs excluded"));
    append(pulsePanel, pulse, button("How this report works  →", "system-link", () => goToView("system")));
    append(stagePanel, stageList);
    append(rail, stagePanel, pulsePanel);
    append(grid, focusPanel, rail);
    view.appendChild(grid);

    const signals = element("section", "brief-signals");
    signals.setAttribute("aria-label", "Portfolio decisions and evidence gaps");
    append(signals,
      briefSignalPanel(
        "decisions",
        "Human judgment",
        "Decisions to make",
        snapshot.brief.decisions || [],
        "No explicit decisions are waiting in this snapshot.",
        "decision"
      ),
      briefSignalPanel(
        "gaps",
        "Known unknowns",
        "Evidence gaps",
        snapshot.brief.evidenceGaps || [],
        "No consequential evidence gaps were recorded for this snapshot.",
        "gap"
      ));
    view.appendChild(signals);

    const horizon = element("section", "horizon");
    const sectionTitle = append(element("div", "section-title"), append(element("div"), element("p", "kicker", "Forward motion"), element("h2", "", "Ready to advance")), element("p", "", "High-leverage next moves after the current blockers and decisions."));
    const moveGrid = element("div", "move-grid");
    const cards = ready.length ? ready : present.filter((project) => !project.attention).slice(0, 3);
    cards.forEach((project, index) => {
      const card = element("button", "move-card");
      card.type = "button";
      card.addEventListener("click", (event) => openProject(project.id, event.currentTarget));
      append(card, element("span", "move-number", String(index + 1).padStart(2, "0")), statusNode(project.tone, project.health), element("span", "move-title", project.name), element("span", "move-copy", project.next), append(element("span", "move-foot"), document.createTextNode(project.stage), element("b", "", "Open brief ↗")));
      moveGrid.appendChild(card);
    });
    append(horizon, sectionTitle, moveGrid);
    view.appendChild(horizon);
    return view;
  }

  function renderPortfolio() {
    const projects = snapshot.projects;
    const term = state.query.trim().toLowerCase();
    const filtered = projects.filter((project) => {
      const text = [project.name, project.summary, project.stack, project.stage, project.health].join(" ").toLowerCase();
      const repository = repositoryOf(project);
      const matchesText = !term || text.includes(term);
      const matchesFilter = state.filter === "all" ||
        (state.filter === "attention" && project.attention) ||
        (state.filter === "active" && repository.changeCount > 0) ||
        (state.filter === "clean" && repository.state === "clean") ||
        (state.filter === "missing" && !project.present);
      return matchesText && matchesFilter;
    });
    const view = element("section", "view portfolio-view");
    append(view, append(element("div", "view-intro"), element("p", "kicker", "Portfolio ledger · " + projects.length + " records"), element("h1", "", "Every project, ordered by signal."), element("p", "", "Search by project, stack, phase, or health. Open any row for current evidence, risk, next move, and a safe Git change plan.")));
    const tools = element("div", "portfolio-tools");
    const search = element("label", "search-box");
    const input = element("input");
    input.type = "search";
    input.placeholder = "Project, stack, phase…";
    input.value = state.query;
    input.setAttribute("aria-label", "Search projects");
    input.addEventListener("input", (event) => { state.query = event.target.value; render(); focusSearch(state.query.length); });
    append(search, element("span", "", "Search"), input, element("kbd", "", "/"));
    const filters = element("div", "filter-group");
    filters.setAttribute("aria-label", "Portfolio filters");
    const definitions = [
      ["all", "All", projects.length],
      ["attention", "Attention", projects.filter((project) => project.attention).length],
      ["active", "Local work", projects.filter((project) => repositoryOf(project).changeCount > 0).length],
      ["clean", "Clean", projects.filter((project) => repositoryOf(project).state === "clean").length],
      ["missing", "Missing", projects.filter((project) => !project.present).length],
    ];
    definitions.forEach(([id, label, count]) => {
      const filterButton = element("button");
      filterButton.type = "button";
      filterButton.dataset.filterId = id;
      filterButton.setAttribute("aria-pressed", String(state.filter === id));
      append(filterButton, document.createTextNode(label + " "), element("span", "", String(count).padStart(2, "0")));
      filterButton.addEventListener("click", () => {
        state.filter = id;
        render();
        requestAnimationFrame(() => {
          const restored = document.querySelector('[data-filter-id="' + id + '"]');
          if (restored) restored.focus();
        });
      });
      filters.appendChild(filterButton);
    });
    append(tools, search, filters);
    const panel = element("div", "panel portfolio-panel");
    panel.appendChild(projectTable(filtered));
    append(view, tools, panel, element("p", "ledger-note", filtered.length + " of " + projects.length + " projects shown · Snapshot evidence, not live telemetry"));
    return view;
  }

  function focusSearch(position) {
    requestAnimationFrame(() => {
      const input = document.querySelector(".search-box input");
      if (input) { input.focus(); input.setSelectionRange(position, position); }
    });
  }

  function renderActivity() {
    const projects = snapshot.projects;
    const items = snapshot.activity || [];
    const commits = projects.filter((project) => repositoryOf(project).lastCommit);
    commits.sort((a, b) => repositoryOf(b).lastCommit.at.localeCompare(repositoryOf(a).lastCommit.at));
    const evidence = projects.filter((project) => project.lastActivity && project.lastActivity.kind === "evidence" && project.lastActivity.on).sort((a, b) => b.lastActivity.on.localeCompare(a.lastActivity.on));
    const observed = projects.filter((project) => project.lastActivity && project.lastActivity.on).sort((a, b) => a.lastActivity.on.localeCompare(b.lastActivity.on));
    const view = element("section", "view activity-view");
    append(view, append(element("div", "view-intro"), element("p", "kicker", "Evidence trail · newest first"), element("h1", "", "What moved across the portfolio."), element("p", "", "Recent commits and approved operational evidence. Activity is factual evidence; it is not a completion score.")));
    const layout = element("div", "activity-layout");
    const panel = element("div", "panel activity-panel");
    const head = element("div", "activity-head");
    ["Date", "Type", "Project", "Observed movement"].forEach((label) => head.appendChild(element("span", "", label)));
    panel.appendChild(head);
    items.forEach((item) => {
      const project = projects.find((candidate) => candidate.id === item.projectId);
      const dateNode = append(element("span", "activity-date"), document.createTextNode(formatDate(item.on, false)), element("small", "", item.on.slice(0, 4)));
      append(panel, append(element("div", "activity-row"), dateNode, element("span", "activity-type", item.type), element("strong", "", project ? project.name : item.projectId), element("p", "", item.note)));
    });
    if (!items.length) panel.appendChild(append(element("div", "empty-state"), element("strong", "", "No reviewed activity yet."), element("span", "", "Activity appears only when a bounded source supports it.")));
    const aside = element("aside", "panel activity-aside");
    const attention = projects.filter((project) => project.attention).length;
    append(aside, element("p", "kicker", "Read the signal"), element("h2", "", "Momentum is uneven by design."), element("p", "", (commits[0] ? commits[0].name : "No project") + " has the freshest recorded commit. " + (evidence[0] ? evidence[0].name : "No project") + " has the freshest approved evidence. " + attention + " decision or validation gate" + (attention === 1 ? " needs" : "s need") + " human judgment."));
    const dl = element("dl");
    const fact = (term, value) => append(element("div"), element("dt", "", term), element("dd", "", value));
    append(dl,
      fact("Freshest commit", commits[0] ? commits[0].name + " · " + formatDate(repositoryOf(commits[0]).lastCommit.at, false) : "None"),
      fact("Freshest evidence", evidence[0] ? evidence[0].name + " · " + formatDate(evidence[0].lastActivity.on, false) : "None"),
      fact("Longest quiet", observed[0] ? observed[0].name + " · " + formatDate(observed[0].lastActivity.on, false) : "None"));
    aside.appendChild(dl);
    append(layout, panel, aside);
    view.appendChild(layout);
    return view;
  }

  function systemCard(index, tone, status, title, body, facts) {
    const card = element("article", "system-card");
    append(card, element("span", "system-number", String(index).padStart(2, "0")), statusNode(tone, status), element("h2", "", title), element("p", "", body));
    const dl = element("dl");
    facts.forEach(([term, value]) => append(dl, append(element("div"), element("dt", "", term), element("dd", "", value))));
    card.appendChild(dl);
    return card;
  }

  function renderSystem() {
    const projects = snapshot.projects;
    const clean = projects.filter((project) => repositoryOf(project).state === "clean").length;
    const local = projects.filter((project) => repositoryOf(project).changeCount > 0).length;
    const view = element("section", "view system-view");
    append(view, append(element("div", "view-intro"), element("p", "kicker", "System / evidence boundary"), element("h1", "", "Honest signals, deliberately limited."), element("p", "", "This release reports repository and approved project-document state. It does not claim live CPU, memory, service, port, CI, or deployment health.")));
    const grid = element("div", "system-grid");
    append(grid,
      systemCard(1, "good", "Connected", "Workspace intelligence", "Project identities, bounded Git facts, reviewed risks, and documented next actions were included in this validated snapshot.", [["Projects", projects.length], ["Clean trees", clean], ["Local WIP", local]]),
      systemCard(2, "neutral", "Not connected", "Runtime telemetry", "No host agent or runtime API is connected, so this site will not invent resource, process, service, or network readings.", [["CPU", "—"], ["Memory", "—"], ["Services", "—"]]),
      systemCard(3, "info", "Protected", "Source boundaries", "Environment files, provider caches, raw datasets, databases, traces, logs, credentials, user records, and full source paths stay out of the site.", [["Secrets", "Excluded"], ["Raw data", "Excluded"], ["Paths", "Relative labels only"]]));
    view.appendChild(grid);
    const refresh = element("section", "refresh-model");
    append(refresh, append(element("div"), element("p", "kicker", "Refresh model"), element("h2", "", "A current report comes from a validated build.")), element("p", "", "The workflow collects bounded local facts, reviews only allowlisted evidence, verifies that evidence did not change during review, finalizes the sanitized snapshot, and deterministically creates this local site."));
    const steps = element("div", "refresh-steps");
    ["Collect bounded repository facts", "Review allowlisted evidence", "Verify and finalize snapshot", "Build and validate local site"].forEach((label, index) => append(steps, append(element("span"), element("b", "", String(index + 1).padStart(2, "0")), document.createTextNode(label))));
    refresh.appendChild(steps);
    view.appendChild(refresh);
    return view;
  }

  function worktreeSummary(repository) {
    if (repository.state === "unavailable") return "Repository state unavailable";
    if (!repository.changeCount) return "No uncommitted changes";
    const parts = [];
    if (repository.conflictedCount) parts.push(countNoun(repository.conflictedCount, "conflict"));
    if (repository.modifiedCount) parts.push(countNoun(repository.modifiedCount, "tracked update"));
    if (repository.deletedCount) parts.push(countNoun(repository.deletedCount, "deletion"));
    if (repository.untrackedCount) parts.push(countNoun(repository.untrackedCount, "untracked change"));
    return countNoun(repository.changeCount, "change") + " total · " + parts.join(" · ");
  }

  function stagingSummary(repository) {
    if (repository.state === "unavailable") return "Counts could not be collected.";
    if (repository.conflictedCount) return "Conflicts must be resolved before a clean commit can be prepared.";
    const parts = [];
    if (repository.stagedCount) parts.push(countNoun(repository.stagedCount, "staged change"));
    if (repository.unstagedCount) parts.push(countNoun(repository.unstagedCount, "unstaged tracked change"));
    if (repository.untrackedCount) parts.push(countNoun(repository.untrackedCount, "untracked change"));
    return parts.length ? parts.join(" · ") : "Nothing is waiting to be staged.";
  }

  function outgoingSummary(repository) {
    const outgoing = repository.outgoing || {};
    if (outgoing.status === "known") return outgoing.count ? countNoun(outgoing.count, "commit") + " not present in the locally recorded upstream." : "No commits are ahead of the locally recorded upstream.";
    if (outgoing.status === "no-upstream") return "Push state is unavailable because no upstream is configured.";
    if (outgoing.status === "unborn") return "No commit history exists yet.";
    return "Outgoing commit state could not be collected.";
  }

  function outgoingBadge(repository) {
    const outgoing = repository.outgoing || {};
    if (outgoing.status === "known") return outgoing.count ? String(outgoing.count).padStart(2, "0") + " outgoing" : "Up to date";
    if (outgoing.status === "no-upstream") return "No upstream";
    if (outgoing.status === "unborn") return "No history";
    return "Unavailable";
  }

  function suggestion(kind, repository) {
    if (kind === "resolve-conflicts") return ["Resolve " + countNoun(repository.conflictedCount, "conflict"), "Clear conflicted entries, then review the resulting staged and unstaged work."];
    if (kind === "review-initial-commit") return ["Prepare the first commit", "Review all local changes and group a coherent starting point."];
    if (kind === "commit-staged") return ["Commit " + countNoun(repository.stagedCount, "staged change"), "The index already contains work that can become the next reviewed commit."];
    if (kind === "stage-tracked") return ["Review " + countNoun(repository.unstagedCount, "unstaged tracked change"), "Stage a coherent set after checking that the changes belong together."];
    return ["Review " + countNoun(repository.untrackedCount, "untracked change"), "Decide which new work belongs in source control before adding it."];
  }

  async function writeClipboard(value) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try { await navigator.clipboard.writeText(value); return; } catch (_) { /* use bounded fallback */ }
    }
    const textarea = element("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      if (!document.execCommand("copy")) throw new Error("copy rejected");
    } finally {
      textarea.remove();
    }
  }

  async function copyValue(value, label, buttonNode) {
    const original = buttonNode.textContent;
    try {
      await writeClipboard(value);
      buttonNode.textContent = "Copied";
      liveRegion.textContent = label + " copied.";
    } catch (_) {
      buttonNode.textContent = "Try again";
      liveRegion.textContent = "Copy failed. Select the text manually.";
    }
    window.setTimeout(() => { if (buttonNode.isConnected) buttonNode.textContent = original; }, 2200);
  }

  function openProject(projectId, trigger) {
    returnFocus = trigger || document.activeElement;
    state.selectedId = projectId;
    renderDrawer();
  }

  function closeProject() {
    state.selectedId = null;
    renderDrawer();
    if (returnFocus && returnFocus.isConnected) returnFocus.focus();
    returnFocus = null;
  }

  function setBackgroundInert(active) {
    [document.querySelector(".site-header"), root, document.querySelector(".site-footer")].forEach((node) => {
      if (!node) return;
      node.inert = active;
      if (active) node.setAttribute("aria-hidden", "true");
      else node.removeAttribute("aria-hidden");
    });
  }

  function trapDrawerFocus(event) {
    if (event.key !== "Tab" || !state.selectedId) return;
    const drawer = drawerRoot.querySelector(".project-drawer");
    if (!drawer) return;
    const focusable = Array.from(
      drawer.querySelectorAll('button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter((node) => !node.hidden);
    if (!focusable.length) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    } else if (!drawer.contains(document.activeElement)) {
      event.preventDefault();
      first.focus();
    }
  }

  function renderDrawer() {
    drawerRoot.replaceChildren();
    document.body.style.overflow = state.selectedId ? "hidden" : "";
    setBackgroundInert(Boolean(state.selectedId));
    if (!state.selectedId) return;
    const project = snapshot.projects.find((candidate) => candidate.id === state.selectedId);
    if (!project) return;
    const repository = repositoryOf(project);
    const layer = element("div", "drawer-layer");
    layer.addEventListener("mousedown", (event) => { if (event.target === layer) closeProject(); });
    const drawer = element("aside", "project-drawer");
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "true");
    drawer.setAttribute("aria-labelledby", "drawer-title");
    const close = button("Close  ×", "drawer-close", closeProject);
    close.setAttribute("aria-label", "Close project brief");
    append(drawer, append(element("div", "drawer-top"), element("span", "drawer-index", String(snapshot.projects.indexOf(project) + 1).padStart(2, "0") + " / " + snapshot.projects.length), close));
    const title = element("div", "drawer-title");
    const heading = element("h2", "", project.name);
    heading.id = "drawer-title";
    append(title, element("p", "kicker", project.stage + " · " + project.stack), heading, statusNode(project.tone, project.health));
    append(drawer, title, element("p", "drawer-summary", project.summary));
    const risk = append(element("div", "drawer-block risk-block"), element("span", "block-label", "Current risk"), element("p", "", project.risk));
    const nextCopy = button("Copy prompt", "copy-next", (event) => copyValue(project.next, "Next action", event.currentTarget));
    nextCopy.setAttribute("aria-label", "Copy next action for " + project.name);
    const next = append(element("div", "drawer-block next-block"), append(element("div", "block-label-row"), element("span", "block-label", "Best next move"), nextCopy), element("p", "", project.next));
    append(drawer, risk, next);

    const grid = element("div", "git-grid");
    const gridFact = (term, value) => append(element("div"), element("span", "", term), element("strong", "", value));
    append(grid, gridFact("Branch", branchLabel(project)), gridFact("Worktree", gitLabel(project)), gridFact("Last evidence", activityLabel(project)), gridFact("Evidence source", project.evidence));
    drawer.appendChild(grid);

    const gitSection = element("section", "drawer-git-state");
    gitSection.setAttribute("aria-labelledby", "drawer-git-title");
    const gitHeading = append(element("div", "drawer-section-heading"), element("p", "kicker", "Repository snapshot"), element("h3", "", "Git change plan"));
    gitHeading.lastChild.id = "drawer-git-title";
    const uncommitted = append(element("article", "git-state-card"), element("span", "block-label", "Uncommitted changes"), element("strong", "", worktreeSummary(repository)), element("p", "", stagingSummary(repository)));
    const outgoing = element("article", "git-state-card");
    append(outgoing, append(element("div", "git-card-title"), element("span", "block-label", "Commits not pushed"), element("b", "", outgoingBadge(repository))), element("p", "", outgoingSummary(repository)));
    const outgoingList = element("ol", "outgoing-list");
    ((repository.outgoing && repository.outgoing.commits) || []).forEach((commit, index) => append(outgoingList, append(element("li"), element("span", "", String(index + 1).padStart(2, "0")), element("strong", "", commit.subject || "Commit subject withheld"), element("time", "", formatDate(commit.at, false)))));
    if (outgoingList.children.length) outgoing.appendChild(outgoingList);
    if (repository.outgoing && repository.outgoing.status === "known") outgoing.appendChild(element("p", "drawer-footnote", "Compared with the locally recorded upstream without fetching a remote." + (repository.outgoing.truncated ? " Only the newest eight commits are shown." : "")));
    const suggestions = element("article", "git-state-card");
    suggestions.appendChild(element("span", "block-label", "Potential commits"));
    const suggestionsList = element("ul", "commit-suggestions");
    (repository.commitSuggestionKinds || []).forEach((kind) => {
      const [titleText, detail] = suggestion(kind, repository);
      append(suggestionsList, append(element("li"), element("span", "", "→"), append(element("div"), element("strong", "", titleText), element("p", "", detail))));
    });
    if (suggestionsList.children.length) suggestions.appendChild(suggestionsList);
    else suggestions.appendChild(element("p", "", repository.state === "clean" ? "No commit is suggested while the worktree is clean." : "No safe suggestion is available from the collected counts."));
    append(gitSection, gitHeading, uncommitted, outgoing, suggestions);
    drawer.appendChild(gitSection);

    const lastCommit = repository.lastCommit && (repository.lastCommit.subject || "Commit subject withheld");
    append(drawer, append(element("div", "drawer-commit"), element("span", "block-label", "Last recorded commit"), element("p", "", lastCommit || "No commit history")));
    const pathButton = element("button", "copy-path");
    pathButton.type = "button";
    const pathLabel = append(element("span"), element("small", "", "Relative project label"), element("strong", "", "projects/" + project.id));
    const pathAction = element("b", "", "Copy");
    pathButton.addEventListener("click", () => copyValue("projects/" + project.id, "Relative project label", pathAction));
    append(pathButton, pathLabel, pathAction);
    append(drawer, pathButton, element("p", "drawer-footnote", "Resolve this label only against the approved projects root. Absolute source paths stay private."));
    layer.appendChild(drawer);
    drawerRoot.appendChild(layer);
    requestAnimationFrame(() => close.focus());
  }

  function goToView(view) {
    if (!views.has(view)) return;
    state.view = view;
    state.selectedId = null;
    render();
    const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  }

  function render() {
    document.querySelectorAll("[data-view-target]").forEach((node) => {
      node.setAttribute("aria-current", node.dataset.viewTarget === state.view ? "page" : "false");
    });
    const factories = { brief: renderBrief, portfolio: renderPortfolio, activity: renderActivity, system: renderSystem };
    root.replaceChildren(factories[state.view]());
    renderDrawer();
  }

  function fail(message) {
    const section = append(element("section", "error-state"), element("p", "kicker", "Snapshot unavailable"), element("h1", "", "This local build cannot be displayed."), element("p", "", message));
    root.replaceChildren(section);
  }

  if (!snapshot || snapshot.schemaVersion !== 2 || !Array.isArray(snapshot.projects) || !snapshot.brief || !snapshot.coverage) {
    fail("Rebuild the site from a validated Central Projects Tracking schema-v2 snapshot.");
    return;
  }

  document.title = "Central Projects Tracking — " + snapshot.scopeLabel;
  document.getElementById("scope-label").textContent = snapshot.scopeLabel;
  document.getElementById("snapshot-label").textContent = formatDate(snapshot.generatedAt, false) + " UTC";
  document.getElementById("footer-snapshot").textContent = "Evidence snapshot · " + formatDate(snapshot.generatedAt, false) + " UTC";
  document.getElementById("footer-count").textContent = snapshot.projects.filter((project) => project.present).length + " projects under watch";
  document.querySelectorAll("[data-view-target]").forEach((node) => node.addEventListener("click", () => goToView(node.dataset.viewTarget)));
  window.addEventListener("keydown", (event) => {
    trapDrawerFocus(event);
    if (event.key === "Escape" && state.selectedId) closeProject();
    if (event.key === "/" && !state.selectedId && document.activeElement.tagName !== "INPUT") {
      event.preventDefault();
      state.view = "portfolio";
      render();
      focusSearch(state.query.length);
    }
  });
  render();
}());
