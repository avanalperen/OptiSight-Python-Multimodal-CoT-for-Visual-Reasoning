
            const video = document.getElementById('video-feed');
            const canvas = document.getElementById('canvas');
            const photoDisplay = document.getElementById('captured-photo');
            const resultDisplay = document.getElementById('result-display');


            async function setScreenMode(mode, fromEvent = false) {
                const actionBtn = document.getElementById('action-btn');
                const actionZone = document.querySelector('.action-zone');
                const modeControls = document.getElementById('screen-mode-controls');
                const fsActionContainer = document.getElementById('fs-action-container');
                const fsModeContainer = document.getElementById('fs-mode-container');
                const inactiveOverlay = document.getElementById('inactive-view-overlay');
                const banner = document.getElementById('sim-mode-banner');

                const ivoTitle = document.getElementById('ivo-title');
                const ivoDesc = document.getElementById('ivo-desc');
                const ivoIcon = document.getElementById('ivo-icon');

                if (mode === 'fullscreen') {
                    if (!fromEvent) {
                        try {
                            const elem = document.documentElement;
                            if (elem.requestFullscreen) await elem.requestFullscreen();
                            else if (elem.webkitRequestFullscreen) await elem.webkitRequestFullscreen();
                            else if (elem.msRequestFullscreen) await elem.msRequestFullscreen();
                        } catch (err) {
                            logDebug("Native Fullscreen Error: " + err.message);
                        }
                    }

                    document.body.classList.add('fullscreen-active');
                    document.getElementById('btn-window-mode').classList.remove('active');
                    document.getElementById('btn-fullscreen-mode').classList.add('active');

                    // Move elements to fullscreen bar
                    if (fsActionContainer && actionBtn) {
                        fsActionContainer.appendChild(actionBtn);
                        const fsScreenshotBtn = document.getElementById('btn-take-screenshot-fs');
                        if (fsScreenshotBtn) {
                            fsScreenshotBtn.style.display = 'flex';
                            fsActionContainer.appendChild(fsScreenshotBtn); // Appends it after actionBtn (to its right)
                        }
                    }
                    if (fsModeContainer && modeControls) fsModeContainer.appendChild(modeControls);

                    // Show Warning if init mode doesn't match current view
                    if (simInitMode === 'windowed' && habitatSubMode === 'autonomous') {
                        if (ivoTitle) ivoTitle.textContent = "Windowed Mode Selected";
                        if (ivoDesc) ivoDesc.textContent = "Simulator was initialized for the dashboard. For 1080p, please restart in Fullscreen mode.";
                        if (ivoIcon) ivoIcon.textContent = "🪟";
                        if (inactiveOverlay) inactiveOverlay.style.display = 'flex';
                    } else {
                        if (inactiveOverlay) inactiveOverlay.style.display = 'none';
                    }

                    if (banner) banner.style.display = 'none';
                    photoDisplay.style.objectFit = 'fill';
                    video.style.objectFit = 'fill';
                } else {
                    if (!fromEvent && document.fullscreenElement) {
                        try {
                            if (document.exitFullscreen) await document.exitFullscreen();
                            else if (document.webkitExitFullscreen) await document.webkitExitFullscreen();
                            else if (document.msExitFullscreen) await document.msExitFullscreen();
                        } catch (err) {
                            logDebug("Exit Fullscreen Error: " + err.message);
                        }
                    }

                    document.body.classList.remove('fullscreen-active');
                    document.getElementById('btn-window-mode').classList.add('active');
                    document.getElementById('btn-fullscreen-mode').classList.remove('active');

                    // Move elements back to original positions
                    const actionRow = document.getElementById('action-row');
                    const gridWrapper = document.getElementById('grid-controls-wrapper');
                    if (actionRow && actionBtn) {
                        // Insert before grid-controls-wrapper to maintain center position
                        if (gridWrapper) {
                            actionRow.insertBefore(actionBtn, gridWrapper);
                        } else {
                            actionRow.appendChild(actionBtn);
                        }
                    }

                    // Hide fullscreen screenshot button
                    const fsScreenshotBtn = document.getElementById('btn-take-screenshot-fs');
                    if (fsScreenshotBtn) {
                        fsScreenshotBtn.style.display = 'none';
                    }

                    // Restore mode controls to original menu location
                    const clearBtn = document.getElementById('btn-clear-result');
                    if (clearBtn && clearBtn.parentElement && modeControls) {
                        clearBtn.parentElement.insertBefore(modeControls, clearBtn);
                    }

                    // Show Warning if init mode doesn't match current view
                    if (simInitMode === 'fullscreen' && habitatSubMode === 'autonomous') {
                        if (ivoTitle) ivoTitle.textContent = "Fullscreen Mode Selected";
                        if (ivoDesc) ivoDesc.textContent = "Simulator was initialized for 1080p. Dashboard preview is disabled.";
                        if (ivoIcon) ivoIcon.textContent = "📺";
                        if (inactiveOverlay) inactiveOverlay.style.display = 'flex';
                    } else {
                        if (inactiveOverlay) inactiveOverlay.style.display = 'none';
                    }

                    if (banner) banner.style.display = 'none';
                    photoDisplay.style.objectFit = 'fill';
                    video.style.objectFit = 'fill';
                }
                logDebug(`Screen mode changed to: ${mode}`);
            }

            // Sync UI state when native fullscreen is toggled (e.g. via ESC key)
            document.addEventListener('fullscreenchange', () => {
                if (!document.fullscreenElement && document.body.classList.contains('fullscreen-active')) {
                    setScreenMode('window', true);
                }
            });

            function updateFullscreenStatusLabel(status) {
                const label = document.getElementById('fs-status-label');
                if (!label) return;

                label.textContent = status;
                label.className = ''; // Reset classes

                if (status === 'INACTIVE') label.classList.add('status-inactive');
                else if (status === 'STARTED ANALYSING') label.classList.add('status-analysing');
                else if (status === 'IN ACTION') label.classList.add('status-inaction');
                else if (status === 'END') label.classList.add('status-end');
            }

            function scrollToBottom() {
                resultDisplay.scrollTop = resultDisplay.scrollHeight;
            }
            const fpsLabel = document.getElementById('fps-val');
            const actionBtn = document.getElementById('action-btn');
            const promptInput = document.getElementById('prompt-input');
            const placeholder = document.getElementById('placeholder-text');

            // Resource Monitor elements
            const ramVal = document.getElementById('ram-val');
            const gpuVal = document.getElementById('gpu-val');
            const gpuMem = document.getElementById('gpu-mem');

            // Periodic Stats Polling
            async function updateStats() {
                try {
                    const res = await fetch('/stats');
                    const data = await res.json();
                    ramVal.textContent = data.ram + '%';
                    gpuVal.textContent = data.gpu.percent + '%';
                    gpuMem.textContent = data.gpu.usage;

                    // Color coding RAM
                    if (data.ram > 90) ramVal.style.color = '#f44747';
                    else if (data.ram > 70) ramVal.style.color = '#dcdcaa';
                    else ramVal.style.color = '#4ec9b0';
                } catch (e) { }
            }
            setInterval(updateStats, 2000);
            updateStats();

            // File inputs
            const photoUpload = document.getElementById('photo-upload');
            const videoUpload = document.getElementById('video-upload');

            let currentMode = null;
            let streamTimeout = null;
            let lastAnalysisTimestamp = 0;
            let remainingTimeAtPause = 0;
            let captureIntervalSec = 3;
            let currentSourceName = '';
            let isStreaming = false;
            let selectedDevice = 'cuda';
            let isModelLoaded = false;
            let selectedModel = null; // Store chosen model

            let habitatSubMode = 'live'; // NEW: Track habitat sub-mode
            let simInitMode = 'windowed'; // NEW: Track resolution mode chosen at init
            let pendingSceneName = ''; // NEW: Track scene while choosing mode
            let requestedSimWidth = 1920; // NEW: Track actual resolution for overlays
            let requestedSimHeight = 1080; // NEW: Track actual resolution for overlays

            let currentAnalysisController = null; // Controller for cancelling pending requests

            const BASE_PROMPT = "Describe this image";

            // Hierarchical Scenario & Prompt Management
            let currentScenario = 'scenario1';
            let currentPromptTab = 'searching';
            let currentAutomationMode = null; // 'auto' or 'manual'
            let settingsChanged = false;

            // Data structure: scenarios[scenarioId][promptType]
            let scenarios = {
                'scenario1': {
                    'core': "",
                    'searching': "",
                    'finding': "",
                    'navigating': "",
                    'stopping': "",
                    'recovering': ""
                },
                'scenario2': {
                    'core': "",
                    'searching': "",
                    'finding': "",
                    'navigating': "",
                    'stopping': "",
                    'recovering': ""
                }
            };

            function switchScenario(scenarioId) {
                saveActivePromptToMemory();
                currentScenario = scenarioId;

                // UI Update for Scenario Tabs
                document.querySelectorAll('.scenario-tab').forEach(btn => {
                    btn.classList.toggle('active', btn.textContent.toLowerCase().includes(scenarioId.replace('scenario', '')));
                });

                // UI Update for Scenario Pills (Main UI)
                document.querySelectorAll('.scenario-pill').forEach(pill => {
                    pill.classList.toggle('active', pill.getAttribute('onclick').includes(`'${scenarioId}'`));
                });

                // Update core prompt active scenario name
                const corePromptScenarioName = document.getElementById('core-prompt-scenario-name');
                if (corePromptScenarioName) {
                    corePromptScenarioName.textContent = scenarioId === 'scenario1' ? 'Scenario 1' : 'Scenario 2';
                }

                // Toggle Scanning UI visibility based on Scenario 2
                const isScen2 = (scenarioId === 'scenario2');
                const scanNode = document.getElementById('flow-node-scanning');
                const scanArrow = scanNode ? scanNode.nextElementSibling : null;
                const scanPill = document.getElementById('state-pill-scanning');
                const scanTab = document.querySelector('.prompt-tab[data-tab="scanning"]');
                
                if (scanNode) scanNode.style.display = isScen2 ? '' : 'none';
                if (scanArrow && scanArrow.classList.contains('flow-arrow')) scanArrow.style.display = isScen2 ? '' : 'none';
                if (scanPill) scanPill.style.display = isScen2 ? '' : 'none';
                if (scanTab) scanTab.style.display = isScen2 ? '' : 'none';

                // Default to Core prompt when clicking/switching scenario
                switchCoTPromptTab('core', true);
            }

            function setAutomationMode(mode) {
                currentAutomationMode = mode;

                // Show content area
                const content = document.getElementById('cot-navigator-content');
                if (content) content.style.display = 'block';

                // Update Buttons
                document.getElementById('mode-toggle-auto').classList.toggle('active', mode === 'auto');
                document.getElementById('mode-toggle-manual').classList.toggle('active', mode === 'manual');

                logDebug(`Mode changed to: ${mode.toUpperCase()}`);

                if (mode === 'manual') {
                    // Manual: Clear active state initially
                    currentPromptTab = null;
                    updateStatePills(null);
                } else {
                    // Auto: Default to searching
                    currentPromptTab = 'searching';
                    switchCoTPromptTab('searching', true);
                    updateStatePills('searching');
                }
                updateActionButton();
            }

            function canTransitionToNavigating() {
                if (!window.true3DProjectionActive) {
                    if (typeof logDebug === 'function') {
                        logDebug("<span style='color: #f44747; font-weight: bold;'>[Restriction] 3D Projection must be active to enter NAVIGATING state.</span>");
                    }
                    return false;
                }
                return true;
            }

            function handleStatePillClick(tab) {
                if (currentAutomationMode === 'manual') {
                    if (currentPromptTab === tab) {
                        // Toggle off
                        switchCoTPromptTab(null, true);
                    } else {
                        if (tab === 'navigating' && !canTransitionToNavigating()) {
                            return;
                        }
                        switchCoTPromptTab(tab, true);
                    }
                } else {
                    // In auto mode, state pills are primarily indicators
                    logDebug("State cannot be changed manually in Automatic mode.");
                }
            }

            async function triggerVisualServo(box) {
                logDebug(`Initiating background Visual Servoing with bbox: [${box.x_min}, ${box.y_min}, ${box.x_max}, ${box.y_max}]`);

                const formData = new FormData();
                formData.append('x_min', box.x_min);
                formData.append('y_min', box.y_min);
                formData.append('x_max', box.x_max);
                formData.append('y_max', box.y_max);
                formData.append('visualize', "true");

                try {
                    const res = await fetch('/start_visual_servo', { method: 'POST', body: formData });
                    const data = await res.json();
                    if (data.status === 'success') {
                        // Start the SSE stream to see the progress
                        if (!isStreaming) {
                            // Ensure navigator has goals/prompts
                            const startFormData = new FormData();
                            startFormData.append('goal', document.getElementById('autonav-target').value);
                            startFormData.append('initial_state', 'NAVIGATING');
                            startFormData.append('device_choice', selectedDevice);
                            startFormData.append('execute_cmds', "true");

                            // We don't need to await start_autonomous_navigate here because start_visual_servo 
                            // already initialized the navigator object. But SSE needs the stream started.

                            // Actually, let's just use toggleAutonomousStream logic but skip the start call
                            // Or just call it with initial_state='VISUAL_LOCK'

                            // To keep it simple and robust, let's just trigger the toggle logic 
                            // but we need to ensure it doesn't overwrite the state we just set.

                            // The cleanest way is to have a specialized stream starter
                            startVisualServoStream();
                        }
                    } else {
                        alert("Visual Servo failed to start: " + data.message);
                    }
                } catch (e) {
                    console.error("Trigger error:", e);
                }
            }

            function startVisualServoStream() {
                if (isStreaming) return;

                // Mirror the toggleAutonomousStream logic but specifically for visual servoing
                const btn = document.getElementById('action-btn');
                const cotOverlay = document.getElementById('cot-overlay');
                const cotContent = document.getElementById('cot-content');

                cotContent.innerHTML = '';
                cotOverlay.style.display = 'block';
                document.getElementById('cot-state').textContent = "NAVIGATING";

                isStreaming = true;
                btn.textContent = "Stop Servo";
                btn.style.backgroundColor = "rgba(204, 0, 0, 0.8)";
                btn.style.color = "white";

                logDebug("Starting Visual Servo Stream...");

                let currentStepResultDiv = null;
                autonavEventSource = new EventSource('/autonomous_navigate_stream');

                autonavEventSource.onmessage = function (event) {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'log') {
                            cotContent.innerHTML += `<div style="color: #bb86fc; margin-top: 8px;">[Servo] ${data.data}</div>`;
                            logDebug(`[VisualServo] ${data.data}`);
                        } else if (data.type === 'state_update') {
                            const stateEl = document.getElementById('cot-state');
                            const state = data.data.state.toUpperCase();
                            stateEl.textContent = state;
                            switchCoTPromptTab(state.toLowerCase(), true);
                        } else if (data.type === 'frame_update') {
                            photoDisplay.src = "data:image/jpeg;base64," + data.data;
                            updateVisualLockOverlay();
                        }
                        else if (data.type === 'stopped' || data.type === 'success') {
                            if (autonavEventSource) {
                                autonavEventSource.close();
                                autonavEventSource = null;
                            }
                            isStreaming = false;
                            btn.textContent = "Start Navigation";
                            btn.style.backgroundColor = "";
                            btn.style.color = "";
                            if (data.type === 'success') {
                                logDebug("<span style='color:#4ec9b0; font-weight:bold;'>Visual Servoing Success! Door Passed.</span>");
                            }
                        }
                        cotOverlay.scrollTop = cotOverlay.scrollHeight;
                    } catch (e) { console.error(e); }
                };
            }

            let lockBoundaries = null;

            let isRecoveryRunning = false;
            async function runRecoverySequence(recoveryInfo) {
                if (isRecoveryRunning) return;
                isRecoveryRunning = true;

                let lastCmd = 'move_forward';
                if (typeof recoveryInfo === 'string' && recoveryInfo.startsWith('START_RECOVERY')) {
                    lastCmd = recoveryInfo.split(':')[1] || 'move_forward';
                }

                logDebug(`<span style="color:#f44747"><b>[System]</b> Collision detected! Initiating automated recovery...</span>`);

                // Determine reverse steps
                let reverseCmd = 'move_backward_small';
                let steps = 5;
                if (lastCmd.includes('left')) {
                    reverseCmd = 'turn_right';
                    steps = lastCmd.includes('90') ? 9 : 3;
                } else if (lastCmd.includes('right')) {
                    reverseCmd = 'turn_left';
                    steps = lastCmd.includes('90') ? 9 : 3;
                } else if (lastCmd.includes('backward')) {
                    reverseCmd = 'move_forward_small';
                }

                logDebug(`<span style="color:#ce9178"><b>[System]</b> Rewinding path (5 steps)...</span>`);
                for (let i = 0; i < 5; i++) {
                    const fd_pop = new FormData();
                    fd_pop.append('command', 'pop_and_restore_pose');
                    const res_pop = await fetch('/move', { method: 'POST', body: fd_pop });
                    const data_pop = await res_pop.json();

                    if (data_pop.frame) {
                        photoDisplay.src = 'data:image/jpeg;base64,' + data_pop.frame;
                    }
                    // Larger delay between steps for a slower, more deliberate rewind
                    await new Promise(r => setTimeout(r, 600));
                }

                logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Recovery complete. State set to SEARCHING.</span>`);
                isRecoveryRunning = false;
                switchCoTPromptTab('searching', true);

                // If in autonomous submode, automatically switch to Auto Mode and start autonomous navigation
                if (habitatSubMode === 'autonomous') {
                    logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Automatically starting Autonomous VLM Search...</span>`);
                    setAutomationMode('auto');
                    toggleAutonomousStream();
                }
            }

            function switchCoTPromptTab(tab, skipSave = false, extraData = null) {
                if (tab === currentPromptTab) return; // Skip if already in this state

                if (!skipSave) {
                    saveActivePromptToMemory();
                }

                currentPromptTab = tab;

                // NEW: Clear SAM box when manually returning to SEARCHING
                if (tab === 'searching') {
                    currentSAMBox = null;
                    updateSAMBoxOverlay();
                    const projBtn = document.getElementById('btn-3d-projection');
                    if (projBtn) {
                        projBtn.disabled = true;
                        projBtn.style.opacity = '0.5';
                        projBtn.style.cursor = 'not-allowed';
                        projBtn.style.background = '';
                        projBtn.style.color = '';
                    }
                }

                // VISUAL LOCK Handling: Draw boundaries from FINDING state
                const lockOverlay = document.getElementById('visual-lock-overlay');
                const lineL = document.getElementById('lock-line-left');
                const lineR = document.getElementById('lock-line-right');

                if (tab === 'visual_lock') {
                    if (lastAngleInfo && lastAngleInfo.box) {
                        lockBoundaries = {
                            x_min: lastAngleInfo.box.x_min,
                            x_max: lastAngleInfo.box.x_max
                        };

                        lockOverlay.style.display = 'block';
                        lineL.style.display = 'block';
                        lineR.style.display = 'block';
                        lineL.style.left = (lockBoundaries.x_min * 100).toFixed(2) + '%';
                        lineR.style.left = (lockBoundaries.x_max * 100).toFixed(2) + '%';

                        updateVisualLockOverlay();

                        logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Visual Lock Engaged. Boundaries frozen at X: ${lockBoundaries.x_min} - ${lockBoundaries.x_max}</span>`);
                    } else {
                        logDebug(`<span style="color:#f44747"><b>[Warning]</b> No bounding box data from FINDING state. Cannot establish lock.</span>`);
                    }
                } else {
                    if (lockOverlay) lockOverlay.style.display = 'none';
                }

                // UI Update for Prompt Tabs
                document.querySelectorAll('.prompt-tab').forEach(btn => {
                    const btnTab = btn.getAttribute('data-tab');
                    btn.classList.toggle('active', tab && btnTab === tab);
                });

                // Check if this is an autonomous state (no VLM prompt)
                const autoStates = ['finding', 'scanning', 'navigating', 'recovering'];
                const editor = document.getElementById('autonav-prompt-editor');
                const noteDisplay = document.getElementById('autonav-note-display');
                const noteText = document.getElementById('auto-note-text');

                // Special handling for Scenario Tab active state when in Core mode
                const scenarioNodes = document.querySelectorAll('.scenario-tab');
                scenarioNodes.forEach(btn => {
                    const isCurrent = btn.textContent.toLowerCase().includes(currentScenario.replace('scenario', ''));
                    btn.classList.toggle('active', tab === 'core' && isCurrent);
                });

                // Show "Core Prompt Active" message if tab is core
                const coreMsg = document.getElementById('core-prompt-msg');
                if (coreMsg) coreMsg.style.display = (tab === 'core') ? 'block' : 'none';

                if (autoStates.includes(tab)) {
                    editor.style.display = 'none';
                    noteDisplay.style.display = 'flex';

                    // Set custom note text
                    if (tab === 'finding') noteText.textContent = "FINDING: No prompt required. Utilizing Grounded-SAM (DINO + SAM 2.1) pipeline to detect target objects and establish spatial coordinates.";
                    else if (tab === 'scanning') noteText.textContent = "SCANNING_PATH: No prompt required. Utilizing depth sensor to identify ground obstacles and determine safe navigation vectors.";
                    else if (tab === 'navigating') noteText.textContent = "NAVIGATING: Performing pure visual servoing to pass through the door and optimize final position.";
                    else if (tab === 'recovering') noteText.textContent = "RECOVERING: Collision detected. Moving to a safe point to restart the search.";
                } else {
                    editor.style.display = 'block';
                    noteDisplay.style.display = 'none';
                }

                // UI Update for Visual Flow Nodes
                document.querySelectorAll('.state-node').forEach(node => {
                    node.classList.remove('active');
                });
                if (tab) {
                    const flowNode = document.getElementById(`flow-node-${tab}`);
                    if (flowNode) {
                        flowNode.classList.add('active');
                    }
                }

                // Sync Main UI pills if they exist
                updateStatePills(tab);

                loadActivePromptFromMemory();

                // SYNC Backend State
                if (tab !== 'core' && tab !== 'manual' && tab !== 'auto') {
                    const stateFd = new FormData();
                    stateFd.append('state', tab);
                    fetch('/set_state', { method: 'POST', body: stateFd })
                        .then(r => r.json())
                        .then(d => {
                            if (d.status === 'success') {
                                // Redundant log removed as per user request
                            } else {
                                logDebug(`<span style="color:#f44747"><b>[Error]</b> State sync failed: ${d.message}</span>`);
                            }
                        }).catch(e => {
                            console.error("State sync error:", e);
                            logDebug(`<span style="color:#f44747"><b>[Error]</b> Connection error during state sync.</span>`);
                        });
                }

                // If entering NAVIGATING state, start manual auto-centering loop
                if (tab === 'navigating' && !isStreaming) {
                    startManualNavigatingLoop();
                }

                // If entering RECOVERING state, trigger automated recovery sequence (only in live manual mode)
                if (tab === 'recovering' && !isStreaming && habitatSubMode !== 'autonomous') {
                    runRecoverySequence(extraData ? extraData.tracking_info : null);
                }

                updateActionButton();
            }

            async function startManualNavigatingLoop() {
                if (currentPromptTab !== 'navigating' || isStreaming) return;

                logDebug("<span style='color: #4ec9b0; font-weight:bold;'>[System] Entering NAVIGATING state. Starting manual centering alignment...</span>");

                let stepCount = 0;
                while (currentPromptTab === 'navigating' && !isStreaming) {
                    const fd = new FormData();
                    fd.append('command', 'auto_align');

                    try {
                        const res = await fetch('/move', { method: 'POST', body: fd });
                        const data = await res.json();

                        if (data.status !== 'success') {
                            logDebug(`<span style="color:#f44747"><b>[System]</b> Alignment loop interrupted: ${data.message}</span>`);
                            break;
                        }

                        // Update Frame and 3D Overlay
                        if (data && data.frame) {
                            photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                        }

                        if (data && data.projection_info && window.true3DProjectionActive) {
                            updateTrue3DOverlay(data.projection_info);
                        }

                        // Periodic heartbeat log
                        stepCount++;
                        if (stepCount % 5 === 0) {
                            const isAligned = data.projection_info && data.projection_info.corners ? "Adjusting..." : "Waiting for 3D Projection...";
                            logDebug(`<span style="color:#9cdcfe; font-size: 12px;">[Navigating] Step ${stepCount}: ${isAligned}</span>`);
                        }

                        // Handle the smooth recovery sequence
                        if (typeof data.tracking_info === 'string' && data.tracking_info.startsWith('START_RECOVERY')) {
                            // Transition to RECOVERING state, which will trigger runRecoverySequence via switchCoTPromptTab
                            switchCoTPromptTab('recovering', true, data);
                            break;
                        }

                        // Handle the smooth clearing sequence
                        if (data.tracking_info === 'START_CLEARING') {
                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Door passage detected. Optimizing position...</span>`);

                            // 2 second initial pause as requested
                            await new Promise(r => setTimeout(r, 2000));

                            for (let i = 0; i < 3; i++) {
                                logDebug(`<span style="color:#ce9178"><b>[System]</b> Clearing step ${i + 1}/3</span>`);
                                const fd_step = new FormData();
                                fd_step.append('command', 'move_forward');
                                const res_step = await fetch('/move', { method: 'POST', body: fd_step });
                                const data_step = await res_step.json();

                                if (data_step.frame) {
                                    photoDisplay.src = 'data:image/jpeg;base64,' + data_step.frame;
                                }
                                await new Promise(r => setTimeout(r, 300));
                            }

                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Mission Completed. Robot stabilized.</span>`);
                            break;
                        }

                        if (data.tracking_info === 'SUCCESS') {
                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Mission Completed. Robot stabilized.</span>`);
                            break;
                        }

                        if (data.state && data.state.toLowerCase() !== 'navigating') {
                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Transition detected: ${data.state}</span>`);
                            switchCoTPromptTab(data.state.toLowerCase(), true);
                            break;
                        }

                        // Small pause to allow visual feedback
                        await new Promise(r => setTimeout(r, 100));

                    } catch (e) {
                        console.error("Manual align error:", e);
                        // Prevent rapid error loops if it's a persistent connection issue
                        await new Promise(r => setTimeout(r, 1000));
                        logDebug(`<span style="color:#f44747"><b>[System]</b> Alignment loop error. See console.</span>`);
                        break;
                    }
                }
                logDebug("<span style='color: #ce9178;'>[System] Manual NAVIGATING loop stopped.</span>");
            }

            function updateStatePills(tab) {
                document.querySelectorAll('.state-pill').forEach(pill => {
                    pill.classList.toggle('active', pill.id === `state-pill-${tab}`);
                });
            }

            function loadActivePromptFromMemory() {
                const tabToLoad = currentPromptTab || 'core';
                const value = scenarios[currentScenario][tabToLoad] || "";
                document.getElementById('autonav-prompt-editor').value = value;
            }

            let isSimLoaded = false;
            function saveActivePromptToMemory() {
                const tabToSave = currentPromptTab || 'core';
                if (!scenarios[currentScenario]) scenarios[currentScenario] = {};
                scenarios[currentScenario][tabToSave] = document.getElementById('autonav-prompt-editor').value;
            }

            function saveActivePromptTab() {
                saveActivePromptToMemory();
                syncScenariosToServer();
                settingsChanged = false;
                // No individual alert as per request
            }

            function updateInitialStateUI(state) {
                // Handle UI Nodes
                const states = ['searching', 'finding', 'scanning', 'navigating', 'stopping', 'recovering'];
                states.forEach(s => {
                    const node = document.getElementById(`flow-node-${s}`);
                    if (node) node.classList.remove('active');
                });

                // Add active to the selected one
                const node = document.getElementById(`flow-node-${state.toLowerCase()}`);
                if (node) node.classList.add('active');
            }

            function setInitialState(state) {
                document.getElementById('autonav-initial-state').value = state;
                updateInitialStateUI(state);
                syncScenariosToServer();
                logDebug(`Initial state set to: ${state}`);
                updateActionButton();
            }

            async function syncScenariosToServer() {
                try {
                    // Save Scenarios
                    await fetch('/save_scenarios', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(scenarios)
                    });

                    // Save Goal Target & Initial State
                    const target = document.getElementById('autonav-target').value;
                    const initialState = document.getElementById('autonav-initial-state').value;
                    const formData = new FormData();
                    formData.append('target', target);
                    formData.append('initial_state', initialState);
                    await fetch('/save_target', {
                        method: 'POST',
                        body: formData
                    });

                    console.log("Scenarios and Goal synced to server.");
                } catch (e) {
                    console.error("Failed to sync settings:", e);
                }
            }

            async function loadScenariosFromServer() {
                try {
                    const res = await fetch('/get_scenarios');
                    const data = await res.json();
                    if (data && typeof data === 'object') {
                        // Merge with defaults to ensure all keys exist
                        scenarios = { ...scenarios, ...data };
                        console.log("Scenarios loaded from server.");
                        loadActivePromptFromMemory();
                    }

                    // Also load settings (Goal Target & Initial State)
                    const sRes = await fetch('/get_settings');
                    const sData = await sRes.json();
                    if (sData) {
                        if (sData.autonav_target !== undefined) {
                            document.getElementById('autonav-target').value = sData.autonav_target;
                        }
                        if (sData.autonav_initial_state !== undefined) {
                            document.getElementById('autonav-initial-state').value = sData.autonav_initial_state;
                            updateInitialStateUI(sData.autonav_initial_state);
                        }
                        console.log("Settings loaded from server.");
                    }
                    // Apply UI logic for current scenario now that data is loaded
                    switchScenario(currentScenario);
                } catch (e) {
                    console.error("Failed to load scenarios/settings:", e);
                }
            }

            function closeAutoNavModal() {
                if (settingsChanged) {
                    if (!confirm("Are you sure? Unsaved changes will be lost.")) return;
                }
                settingsChanged = false;
                document.getElementById('autonav-modal').style.display = 'none';
            }

            function openAutoNavModal() {
                if (!scenarios['scenario1']) {
                    scenarios['scenario1'] = {
                        core: "", searching: "", finding: "",
                        navigating: "",
                        recovering: ""
                    };
                }
                if (!scenarios['scenario2']) {
                    scenarios['scenario2'] = {
                        core: "", searching: "", finding: "",
                        navigating: "",
                        recovering: ""
                    };
                }
                const s1 = scenarios['scenario1'];
                const s2 = scenarios['scenario2'];

                // Reset change tracker
                settingsChanged = false;

                // Add change listeners if not already added
                const editor = document.getElementById('autonav-prompt-editor');
                const target = document.getElementById('autonav-target');
                if (editor && !editor.dataset.listenerAdded) {
                    editor.addEventListener('input', () => { settingsChanged = true; });
                    editor.dataset.listenerAdded = 'true';
                }
                if (target && !target.dataset.listenerAdded) {
                    target.addEventListener('input', () => { settingsChanged = true; });
                    target.dataset.listenerAdded = 'true';
                }

                // Populate defaults ONLY if empty
                if (!s1.core || s1.core.trim() === '') {
                    s1.core = `Task: {goal}.\nOutput: <box>(x1,y1),(x2,y2)</box>`;
                }

                if (!s1.searching || s1.searching.trim() === '') {
                    s1.searching = `Task: Is there a door and door passage visible?
Note: Do not confuse wall corners, pillars, or shower cabin edges with doors. A door passage must be a clear opening meant for walking through into another room.
Respond ONLY with 'Yes' or 'No'. Do not explain.`;
                }

                if (!s1.finding || s1.finding.trim() === '') {
                    s1.finding = s1.core;
                }
                if (!s1.navigating) {
                    s1.navigating = `Goal: {goal}\n<box>(x1,y1),(x2,y2)</box>\n<cmd>Turn [X] Degrees Left/Right</cmd>`;
                }
                if (!s1.stopping) {
                    s1.stopping = `Goal: {goal}\n<cmd>Stop</cmd>`;
                }
                if (!s1.recovering) {
                    s1.recovering = `State: RECOVERING. Is path clear? Respond with 'Clear' or 'Blocked'.`;
                }

                // Populate scenario2 defaults as a copy of scenario1
                if (!s2.core || s2.core.trim() === '') s2.core = s1.core;
                if (!s2.searching || s2.searching.trim() === '') s2.searching = s1.searching;
                if (!s2.finding || s2.finding.trim() === '') s2.finding = s1.finding;
                if (!s2.navigating || s2.navigating.trim() === '') s2.navigating = s1.navigating;
                if (!s2.stopping || s2.stopping.trim() === '') s2.stopping = s1.stopping;
                if (!s2.recovering || s2.recovering.trim() === '') s2.recovering = s1.recovering;

                switchCoTPromptTab(currentPromptTab || 'core', true);
                document.getElementById('autonav-modal').style.display = 'flex';
            }

            function setDevice(device) {
                if (device === 'cpu' && selectedDevice !== 'cpu') {
                    const confirmMessage = "Do you want to continue?\n\nWARNING : IT CAN COLLAPSE YOUR SYSTEM";
                    if (!confirm(confirmMessage)) {
                        return; // Stays on current device
                    }
                }
                selectedDevice = device;
                document.getElementById('device-cpu').classList.toggle('active', device === 'cpu');
                document.getElementById('device-gpu').classList.toggle('active', device === 'cuda');
                console.log("Device selected:", device);

                // If device changes and model was loaded, it will be reloaded on next analysis or manual load
                // For simplicity, we just reset the button state
                resetLoadButton();
            }

            // Tab Switching Logic
            let activePromptTab = 'manual';
            function switchPromptTab(tabId) {
                activePromptTab = tabId;
                document.getElementById('tab-btn-manual').classList.remove('active');
                document.getElementById('tab-btn-auto').classList.remove('active');
                document.getElementById('tab-manual').classList.remove('active');
                document.getElementById('tab-auto').classList.remove('active');

                document.getElementById('tab-btn-' + tabId).classList.add('active');
                document.getElementById('tab-' + tabId).classList.add('active');

                // Re-eval action button state to update text
                updateActionButton();
            }

            function resetLoadButton() {
                const btn = document.getElementById('load-model-btn');
                btn.textContent = "Choose Model";
                btn.style.background = "#444";
                btn.style.color = "#ccc";
                btn.disabled = false;
                isModelLoaded = false;
                selectedModel = null;
            }

            async function toggleLoadModel() {
                const btn = document.getElementById('load-model-btn');

                if (!isModelLoaded) {
                    if (!selectedModel) {
                        // First time: Show model selection modal
                        document.getElementById('model-selection-overlay').style.display = 'flex';
                        return;
                    }

                    // LOAD Path
                    btn.disabled = true;
                    btn.textContent = "Loading...";

                    const formData = new FormData();
                    formData.append('device_choice', selectedDevice);
                    formData.append('model_choice', selectedModel);

                    try {
                        const res = await fetch('/load_model', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await res.json();
                        if (data.status === 'success') {
                            btn.textContent = "Unload Model";
                            btn.style.background = "#007acc";
                            btn.style.color = "white";
                            btn.disabled = false;
                            isModelLoaded = true;

                            // Debug selected model and loading time to Analysis Result screen
                            if (typeof logDebug === 'function') {
                                logDebug(`Model Loaded: ${data.message}`);
                            }

                            // Wait a moment then fetch stats so GPU memory updates correctly
                            setTimeout(updateStats, 1500);
                        } else {
                            btn.textContent = "Retry Load";
                            btn.disabled = false;
                        }
                    } catch (e) {
                        btn.textContent = "Error";
                        btn.disabled = false;
                    }
                } else {
                    // UNLOAD Path
                    btn.disabled = true;
                    btn.textContent = "Unloading...";

                    try {
                        const res = await fetch('/unload_model', { method: 'POST' });
                        const data = await res.json();
                        resetLoadButton();

                        if (typeof logDebug === 'function') {
                            logDebug(data.message || "Model unloaded.");
                        }

                        // Run updateStats after a short delay since unloading takes a moment on CUDA
                        setTimeout(updateStats, 1500);
                    } catch (e) {
                        btn.textContent = "Error Unload";
                        btn.disabled = false;
                    }
                }
            }

            function selectModel(modelName) {
                selectedModel = modelName;
                document.getElementById('model-selection-overlay').style.display = 'none';
                // Trigger the actual load
                toggleLoadModel();
            }

            function cancelCurrentAnalysis() {
                if (currentAnalysisController) {
                    currentAnalysisController.abort();
                    currentAnalysisController = null;
                    console.log("Previous analysis cancelled.");
                }
            }

            function setMode(mode) {
                cancelCurrentAnalysis();
                currentMode = mode;
                currentSourceName = '';
                habitatSubMode = null;

                // 1. GLOBAL UI RESETS
                document.querySelectorAll('.mode-controls button').forEach(b => b.classList.remove('active'));
                document.getElementById(`btn-${mode}`).classList.add('active');

                video.style.display = 'none';
                photoDisplay.style.display = 'none';
                placeholder.style.display = 'block';
                placeholder.textContent = 'Select a Source';
                video.pause();
                video.src = "";
                photoDisplay.src = "";

                document.getElementById('photo-info').style.display = 'none';
                document.getElementById('video-info').style.display = 'none';
                document.getElementById('sim-info').style.display = 'none';
                document.getElementById('photo-upload').value = '';
                document.getElementById('video-upload').value = '';

                // Reset Grids on every tab switch
                document.getElementById('grid-toggle-checkbox').checked = false;
                toggleGrid();
                document.getElementById('angle-grid-checkbox').checked = false;
                toggleAngleGrid();
                currentSAMBox = null;
                updateSAMBoxOverlay();

                stopStream();
                updateActionButton();

                // 2. HABITAT SPECIFIC CLEANUP (Always run)
                document.getElementById('habitat-selection-overlay').style.display = 'none';
                document.getElementById('route-canvas').style.display = 'none';
                const routeCanvas = document.getElementById('route-canvas');
                if (routeCanvas) {
                    const ctx = routeCanvas.getContext('2d');
                    ctx.clearRect(0, 0, routeCanvas.width, routeCanvas.height);
                }
                const cc = document.getElementById('collision-counter');
                if (cc) {
                    cc.textContent = "Collisions: 0";
                    cc.dataset.count = "0";
                    cc.style.display = 'none';
                }
                const fsCc = document.getElementById('fs-collision-counter');
                if (fsCc) {
                    fsCc.textContent = "Collisions: 0";
                    fsCc.dataset.count = "0";
                    fsCc.style.display = 'none';
                }

                // 3. MODE-SPECIFIC SETUP
                document.getElementById('photo-browse-area').style.display = 'none';
                document.getElementById('video-browse-area').style.display = 'none';
                document.getElementById('sim-browse-area').style.display = 'none';

                const fpsControl = document.getElementById('fps-control');
                const heightControl = document.getElementById('height-checkbox-container');

                if (mode === 'photo') {
                    document.getElementById('photo-browse-area').style.display = 'flex';
                    fpsControl.style.display = 'none';
                    heightControl.style.display = 'none';
                } else if (mode === 'video') {
                    document.getElementById('video-browse-area').style.display = 'flex';
                    fpsControl.style.display = 'flex';
                    heightControl.style.display = 'none';
                } else if (mode === 'habitat') {
                    // Reset Habitat initialization state
                    simInitMode = null;
                    const inactiveOverlay = document.getElementById('inactive-view-overlay');
                    if (inactiveOverlay) inactiveOverlay.style.display = 'none';
                    const banner = document.getElementById('sim-mode-banner');
                    if (banner) banner.style.display = 'none';

                    // Ensure we exit fullscreen view UI-wise
                    if (document.body.classList.contains('fullscreen-active')) {
                        setScreenMode('window');
                    }

                    document.getElementById('sim-browse-area').style.display = 'flex';
                    document.getElementById('habitat-selection-overlay').style.display = 'flex';
                    placeholder.textContent = "AI Habitat Interface";
                    fpsControl.style.display = 'none';
                    heightControl.style.display = 'flex';
                }
                updateGridOverlay();
            }

            async function listScenes() {
                try {
                    const res = await fetch('/list_scenes');
                    const data = await res.json();
                    const scenes = data.scenes;

                    const listContainer = document.getElementById('scene-list');
                    listContainer.innerHTML = '';

                    if (scenes.length === 0) {
                        listContainer.innerHTML = '<div style="color:#aaa;">No scenes found in "test habitats"</div>';
                    } else {
                        scenes.forEach(scene => {
                            const btn = document.createElement('button');
                            btn.className = 'habitat-btn';
                            btn.style.width = '80%';
                            btn.style.padding = '10px';
                            btn.style.fontSize = '16px';
                            btn.textContent = scene;
                            btn.onclick = () => loadScene(scene);
                            listContainer.appendChild(btn);
                        });
                    }

                    document.getElementById('scene-selection-overlay').style.display = 'flex';
                } catch (e) {
                    console.error("Failed to list scenes:", e);
                    alert("Failed to list scenes: " + e);
                }
            }

            async function loadScene(sceneName) {
                pendingSceneName = sceneName;
                document.getElementById('scene-selection-overlay').style.display = 'none';
                performSimInit(sceneName);
            }

            async function confirmSimMode(mode, element) {
                // Instantly request native fullscreen synchronously to guarantee gesture permission is not lost!
                if (mode === 'fullscreen') {
                    setScreenMode('fullscreen', false);
                } else {
                    setScreenMode('window', false);
                }

                // Highlight the clicked button
                document.querySelectorAll('.sim-mode-option').forEach(btn => {
                    btn.classList.remove('active');
                });
                if (element) {
                    element.classList.add('active');
                }

                // Add a small delay so the highlight transition is visible
                await new Promise(resolve => setTimeout(resolve, 350));

                simInitMode = mode;
                document.getElementById('sim-mode-modal').style.display = 'none';
            }

            async function performSimInit(sceneName) {
                const formData = new FormData();
                formData.append('scene_name', sceneName);
                const dims = getSimDimensions();
                requestedSimWidth = dims.width;
                requestedSimHeight = dims.height;

                formData.append('width', requestedSimWidth);
                formData.append('height', requestedSimHeight);
                formData.append('hfov', angleSettings.hfov);

                try {
                    const res = await fetch('/init_sim', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        document.getElementById('sim-info').textContent = sceneName;
                        document.getElementById('sim-info').style.display = 'block';
                        currentSourceName = sceneName;
                        updateActionButton();

                        // Initial display state check
                        setScreenMode(simInitMode === 'fullscreen' ? 'fullscreen' : 'window', false);

                        alert("Scene loaded: " + sceneName + " (" + (simInitMode === 'fullscreen' ? '1080p' : 'Windowed') + ")");

                        if (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous') {
                            showMapSelection();
                        } else {
                            // Default fallback
                            document.getElementById('habitat-selection-overlay').style.display = 'flex';
                        }
                    } else {
                        alert("Error loading scene: " + data.message);
                    }
                } catch (e) {
                    console.error("Failed to init sim:", e);
                    alert("Failed to init sim: " + e);
                }
            }

            // Map Selection Logic
            let currentMapInfo = null;

            async function showMapSelection() {
                // Fetch map from backend
                try {
                    const res = await fetch('/get_map', { method: 'POST' });
                    const data = await res.json();

                    if (data.status === 'success') {
                        const img = document.getElementById('topdown-map-img');
                        img.src = 'data:image/jpeg;base64,' + data.map;
                        currentMapInfo = data.info;

                        document.getElementById('map-selection-overlay').style.display = 'flex';
                        // Hide other overlays
                        document.getElementById('habitat-selection-overlay').style.display = 'none';
                        document.getElementById('scene-selection-overlay').style.display = 'none';
                    } else {
                        console.error("Failed to get map:", data.message);
                        alert("Could not generate map for this scene. Starting at default position.");
                        // Fallback to start
                        if (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous') {
                            // Start Live Control immediately
                            // ... Code to start live control view ...
                            startLiveControlView();
                        }
                    }
                } catch (e) {
                    console.error("Network error getting map:", e);
                    // Fallback
                    if (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous') {
                        startLiveControlView();
                    }
                }
            }

            function closeMapOverlay() {
                document.getElementById('map-selection-overlay').style.display = 'none';
                if (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous') {
                    startLiveControlView();
                }
            }

            async function handleMapClick(event) {
                event.stopPropagation();
                if (!currentMapInfo) return;

                const img = document.getElementById('topdown-map-img');
                const rect = img.getBoundingClientRect();

                // Calculate normalized coordinates
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;

                const normX = x / rect.width;
                const normY = y / rect.height;

                console.log(`Map Click: ${x}, ${y} -> Norm: ${normX}, ${normY}`);

                // Show marker
                const marker = document.getElementById('spawn-marker');
                marker.style.left = x + 'px';
                marker.style.top = y + 'px';
                marker.style.display = 'block';

                // Send to backend
                const formData = new FormData();
                formData.append('norm_x', normX);
                formData.append('norm_y', normY);
                formData.append('map_width', currentMapInfo.width);
                formData.append('map_height', currentMapInfo.height);

                try {
                    const res = await fetch('/set_pose', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();

                    if (data.status === 'success') {
                        console.log("Spawn set!");

                        // Immediately update view with the frame from set_pose
                        if (data.frame) {
                            photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                            photoDisplay.style.display = 'block';
                            video.style.display = 'none';
                            placeholder.style.display = 'none';
                        }

                        // Wait a bit to show marker then close
                        setTimeout(() => {
                            closeMapOverlay();
                        }, 200); // Faster close
                    } else {
                        alert("Failed to spawn there: " + data.message);
                    }
                } catch (e) {
                    console.error("Error setting pose:", e);
                }
            }

            async function spawnStarter() {
                try {
                    const res = await fetch('/spawn_starter', { method: 'POST' });
                    const data = await res.json();
                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                        photoDisplay.style.display = 'block';
                        video.style.display = 'none';
                        placeholder.style.display = 'none';
                        closeMapOverlay();
                    } else {
                        alert('Error spawning at starter point: ' + data.message);
                    }
                } catch (e) {
                    console.error("Spawn starter error:", e);
                    alert("Error: " + e);
                }
            }

            function startLiveControlView() {
                // Re-enable controls
                document.addEventListener('keydown', handleLiveControlKey);
                video.style.display = 'none';
                placeholder.style.display = 'none';
                photoDisplay.style.display = 'block';

                const cc = document.getElementById('collision-counter');
                cc.style.display = 'block';
                cc.textContent = 'Collisions: 0';
                cc.dataset.count = "0";

                const fsCc = document.getElementById('fs-collision-counter');
                if (fsCc) {
                    fsCc.style.display = 'inline-block';
                    fsCc.textContent = 'Collisions: 0';
                    fsCc.dataset.count = "0";
                }

                // Fetch initial view
                // fetchInitialView();
                // We removed fetchInitialView here because handleMapClick now sets the view.
                // But if we closed overlay without setting pose (cancel), we might need it.
                // Let's rely on handleMapClick for the spawn case.

                // Setup Interaction
                console.log("Live Control Started");
                logDebug("Live Control Started. Simulator Controls:");
                logDebug("- W/A/S/D: Move Forward/Left/Back/Right");
                logDebug("- Q/Z: Look Up/Down");
                logDebug("- Arrow Keys: Look Up/Down/Left/Right (10°)");
                logDebug("- E: Interact | F: Snap to Floor | 0: Reset Camera");
                logDebug("- ESC: Exit Live Control & Return to Menu");
            }


            let routePoints = [];

            function selectHabitatMode(subMode) {
                habitatSubMode = subMode;
                document.getElementById('habitat-selection-overlay').style.display = 'none';

                // Show Sim Browse Area
                document.getElementById('sim-browse-area').style.display = 'flex';

                // Setup UI for the selected mode
                initHabitatControls(subMode);

                if (subMode === 'autonomous') {
                    // Prompt for display mode ONLY for autonomous
                    document.querySelectorAll('.sim-mode-option').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    document.getElementById('sim-mode-modal').style.display = 'flex';
                } else {
                    // Bypass modal for State Transition and One Shot
                    simInitMode = 'windowed';
                }
            }

            function initHabitatControls(subMode) {
                const actionBtn = document.getElementById('action-btn');
                const screenshotBtn = document.getElementById('btn-take-screenshot');
                const tabBtnAuto = document.getElementById('tab-btn-auto');
                const tabBtnManual = document.getElementById('tab-btn-manual');

                if (subMode === 'live' || subMode === 'live_one_shot' || subMode === 'autonomous') {
                    updateActionButton();
                    actionBtn.style.display = 'block';
                    actionBtn.onclick = handleAction; // Standard analysis loop

                    placeholder.innerHTML = "Browse a Sim, then use Simulator Controls:<br>- W/A/S/D: Move | Q/Z & Arrows: Look 10°<br>- E: Interact | F: Snap to Floor | 0: Reset Camera<br>- ESC: Exit Habitat Live Control";

                    if (subMode === 'live_one_shot') {
                        // Hide CoT Navigator tab
                        if (tabBtnAuto) tabBtnAuto.style.display = 'none';
                        if (tabBtnManual) tabBtnManual.style.display = 'inline-block';
                        switchPromptTab('manual');
                        actionBtn.textContent = "Start Sim Analysis";
                        actionBtn.style.backgroundColor = "rgba(0, 122, 204, 0.8)";
                        actionBtn.style.color = "white";
                    } else if (subMode === 'live' || subMode === 'autonomous') {
                        // Hide Manual Prompt tab for State Transition (live) and Autonomous
                        if (tabBtnManual) tabBtnManual.style.display = 'none';
                        if (tabBtnAuto) tabBtnAuto.style.display = 'block';
                        switchPromptTab('auto');

                        // Configure Automatic Mode for Autonomous VLM
                        const modeToggle = document.getElementById('cot-mode-toggle-group');
                        const screenModeControls = document.getElementById('screen-mode-controls');
                        if (subMode === 'autonomous') {
                            setAutomationMode('auto');
                            if (modeToggle) modeToggle.style.display = 'none';
                            if (screenModeControls) screenModeControls.style.display = 'flex';
                        } else {
                            if (modeToggle) modeToggle.style.display = 'flex';
                            if (screenModeControls) {
                                screenModeControls.style.display = 'none';
                                setScreenMode('window'); // Revert to window mode when leaving Autonomous VLM
                            }
                        }
                    } else {
                        // Show both tabs by default for other modes
                        if (tabBtnAuto) tabBtnAuto.style.display = 'block';
                        if (tabBtnManual) tabBtnManual.style.display = 'block';
                    }

                    // Fetch initial view -> CHANGED to Map Selection
                    if (currentSourceName) {
                        showMapSelection();
                    }

                    if (screenshotBtn) screenshotBtn.style.display = 'flex';
                }

                updateActionButton(); // Re-evaluate button state based on loaded file
            }

            function handleRecordVideo() {
                if (routePoints.length < 2) {
                    alert("Please draw a route with at least 2 points (Start and End).");
                    return;
                }

                const btn = document.getElementById('action-btn');
                btn.disabled = true;
                btn.textContent = "Recording...";

                // Prepare points
                const pointsStr = routePoints.map(p => `${p.x},${p.y},0`).join(';'); // Backend expects x,y or x,y,z? 
                // Wait, the backend generate_video expects start_point and end_point as "x,y,z".
                // We need to clarify if it supports a full path. 
                // The specific request says: "fix angle ile cizilen rotada hareket eden robotun gozunden olan video kaybedilmeli"
                // My backend currently only supports start/end. I will need to update backend too. 
                // For now, let's send what we can.

                // Actually, 3D points from 2D canvas click is hard without a top-down map calibration.
                // Placeholder: We will just trigger the backend generation with random points or if we had a map.
                // Since we don't have a map, clicks on a blank screen are meaningless for coordinates.
                // BUT, the user asked to "draw a route". 
                // I will implement the UI interaction now, and we will mock the coordinates or improve backend 
                // to generated a random valid path if coordinates are not map-relative.

                // Let's assume for now we just trigger the generation as before but with "Record" UI.

                generateVideoFromRoute();
            }

            async function generateVideoFromRoute() {
                // ... call backend
                // Reusing existing generate_video for now, will improve in next step
                const formData = new FormData();
                // formData.append('points', JSON.stringify(routePoints)); // Future

                try {
                    const res = await fetch('/generate_video', { method: 'POST', body: formData });
                    const data = await res.json();
                    if (data.status === 'success') {
                        // Auto play result
                        video.src = data.video_url;
                        video.style.display = 'block';
                        placeholder.style.display = 'none';
                        document.getElementById('route-canvas').style.display = 'none'; // Hide drawing
                    } else {
                        alert("Error: " + data.message);
                    }
                } catch (e) {
                    alert("Error: " + e);
                }

                const btn = document.getElementById('action-btn');
                btn.disabled = false;
                btn.textContent = "Record Video";
            }

            // Route Drawing Interactions
            const rc = document.getElementById('route-canvas');
            rc.addEventListener('click', (e) => {
                if (habitatSubMode !== 'record') return;

                const rect = rc.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // Visual feedback
                const ctx = rc.getContext('2d');
                ctx.fillStyle = '#007acc';
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fill();

                if (routePoints.length > 0) {
                    const last = routePoints[routePoints.length - 1];
                    ctx.strokeStyle = '#007acc';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(last.visX, last.visY); // Use visual coords
                    ctx.lineTo(x, y);
                    ctx.stroke();
                }

                // Store normalized or visual coords? 
                // Without map, visual is all we have. 
                routePoints.push({ visX: x, visY: y, x: x / rect.width, y: y / rect.height });
            });

            function handleLiveControlKey(e) {
                if (currentMode === 'habitat' && !isStreaming) {
                    // Determine action
                    let action = '';
                    const key = e.key; // Use case-sensitive but check lower for standard keys
                    const keyLower = key.toLowerCase();

                    if (keyLower === 'w') action = 'move_forward';
                    else if (keyLower === 's') action = 'move_backward';
                    else if (keyLower === 'a') action = 'turn_left';
                    else if (keyLower === 'd') action = 'turn_right';
                    else if (keyLower === 'q') action = 'look_up';
                    else if (keyLower === 'z') action = 'look_down';

                    else if (key === 'ArrowUp') {
                        const heightActive = document.getElementById('height-toggle-checkbox') && document.getElementById('height-toggle-checkbox').checked;
                        if (heightActive) {
                            adjustHeight(0.1);
                            return;
                        } else {
                            action = 'look_up';
                        }
                    }
                    else if (key === 'ArrowDown') {
                        const heightActive = document.getElementById('height-toggle-checkbox') && document.getElementById('height-toggle-checkbox').checked;
                        if (heightActive) {
                            adjustHeight(-0.1);
                            return;
                        } else {
                            action = 'look_down';
                        }
                    }
                    else if (key === 'ArrowLeft') action = 'turn_left';
                    else if (key === 'ArrowRight') action = 'turn_right';
                    else if (keyLower === 'e') {
                        console.log("Interact triggered");
                        triggerInteract();
                        return;
                    }
                    else if (key === '0') {
                        console.log("Reset Camera triggered");
                        resetCamera();
                        return;
                    }
                    else if (keyLower === 'f') {
                        console.log("Snap to Floor triggered");
                        snapToFloor();
                        return;
                    }
                    else if (key === 'Escape') {
                        console.log("Exiting Live Control");
                        exitLiveControl();
                        return;
                    }

                    if (action) {
                        sendMoveCommand(action);
                    }
                }
            }

            async function setHeight(val) {
                currentHeightOffset = val;
                await updateHeightOnServer();
            }

            async function adjustHeight(delta) {
                currentHeightOffset = Math.max(-1.2, Math.min(1.0, currentHeightOffset + delta));
                await updateHeightOnServer();
            }

            async function updateHeightOnServer() {
                updateHeightLabel();
                await saveHeightSettings();
            }

            function exitLiveControl() {
                // Remove listener
                document.removeEventListener('keydown', handleLiveControlKey);
                document.getElementById('collision-counter').style.display = 'none';
                const fsCc = document.getElementById('fs-collision-counter');
                if (fsCc) fsCc.style.display = 'none';

                // Return to Habitat Selection UI
                document.getElementById('habitat-selection-overlay').style.display = 'flex';
                photoDisplay.style.display = 'none';
                placeholder.style.display = 'block';

                // Clear current sub mode state
                habitatSubMode = null;
                isSimLoaded = false; // Reset sim state on exit
                updateActionButton();
            }

            async function resetCamera() {
                try {
                    const res = await fetch('/reset_camera', { method: 'POST' });
                    const data = await res.json();
                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                    }
                } catch (e) { console.error("Reset Camera error:", e); }
            }

            async function snapToFloor() {
                try {
                    const res = await fetch('/snap_to_floor', { method: 'POST' });
                    const data = await res.json();
                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                    }
                } catch (e) { console.error("Snap to Floor error:", e); }
            }

            async function triggerInteract() {
                try {
                    const formData = new FormData();
                    // No specific body needed for now

                    const res = await fetch('/interact', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();

                    if (data.status === 'success') {
                        // Update view if frame returned
                        if (data.frame) {
                            const img = document.getElementById('captured-photo');
                            img.src = 'data:image/jpeg;base64,' + data.frame;
                            img.style.display = 'block';
                            video.style.display = 'none';
                        }
                        console.log("Interaction success:", data.message);
                    } else {
                        console.error("Interaction failed:", data.message);
                    }
                } catch (e) {
                    console.error("Interaction network error:", e);
                }
            }

            function updateTrue3DOverlay(projInfo) {
                const svgOverlay = document.getElementById('true-3d-overlay');
                const polygon = document.getElementById('true-3d-polygon');
                if (!svgOverlay || !polygon || !projInfo || !projInfo.corners) return;

                const activeEl = (currentMode === 'photo' || currentMode === 'habitat') ? photoDisplay : video;
                if (!activeEl || activeEl.offsetParent === null) return;

                const containerWidth = activeEl.clientWidth;
                const containerHeight = activeEl.clientHeight;

                let displayedW, displayedH, offsetX = 0, offsetY = 0;

                // Always use contain logic to support both legacy and optimized modes without distortion
                let intrinsicWidth = (activeEl.tagName === 'IMG') ? activeEl.naturalWidth : activeEl.videoWidth;
                let intrinsicHeight = (activeEl.tagName === 'IMG') ? activeEl.naturalHeight : activeEl.videoHeight;

                // Fallback to requested resolution if intrinsic size not yet available
                if (!intrinsicWidth || !intrinsicHeight) {
                    intrinsicWidth = requestedSimWidth;
                    intrinsicHeight = requestedSimHeight;
                }

                const containerRatio = containerWidth / containerHeight;
                const contentRatio = intrinsicWidth / intrinsicHeight;
                const isFillMode = activeEl.style.objectFit === 'fill';

                if (isFillMode) {
                    displayedW = containerWidth;
                    displayedH = containerHeight;
                    offsetX = 0;
                    offsetY = 0;
                } else {
                    if (containerRatio > contentRatio) {
                        displayedH = containerHeight;
                        displayedW = containerHeight * contentRatio;
                        offsetX = (containerWidth - displayedW) / 2;
                    } else {
                        displayedW = containerWidth;
                        displayedH = containerWidth / contentRatio;
                        offsetY = (containerHeight - displayedH) / 2;
                    }
                }

                // Add activeEl offset to align with image inside container
                offsetX += activeEl.offsetLeft;
                offsetY += activeEl.offsetTop;

                let pointsStr = "";
                let anyBehind = false;

                for (let i = 0; i < projInfo.corners.length; i++) {
                    const c = projInfo.corners[i];
                    if (c.behind) anyBehind = true;

                    // Map normalized coordinates [0, 1] to actual displayed image area
                    const screenX = offsetX + c.x * displayedW;
                    const screenY = offsetY + c.y * displayedH;
                    pointsStr += `${screenX},${screenY} `;
                }

                if (anyBehind) {
                    // Hide if too close or behind
                    svgOverlay.style.display = 'none';
                } else {
                    svgOverlay.style.display = 'block';
                    polygon.setAttribute("points", pointsStr.trim());
                    
                    // Route drawing logic (bottom center of screen to bottom center of polygon)
                    const routePath = document.getElementById('true-3d-route');
                    if (routePath) {
                        // Find lowest Y points of polygon to find bottom center
                        let minX = 99999, maxX = -99999, maxY = -99999;
                        for (let i = 0; i < projInfo.corners.length; i++) {
                            const c = projInfo.corners[i];
                            const screenX = offsetX + c.x * displayedW;
                            const screenY = offsetY + c.y * displayedH;
                            if (screenY > maxY) maxY = screenY;
                            if (screenX < minX) minX = screenX;
                            if (screenX > maxX) maxX = screenX;
                        }
                        
                        const targetCenterX = (minX + maxX) / 2;
                        const targetBottomY = maxY;
                        
                        const startX = offsetX + (displayedW / 2);
                        const startY = offsetY + displayedH;
                        
                        // Check for evade status
                        const routeStatus = routePath.getAttribute("data-status") || "safe";
                        
                        if (routeStatus === "evade") {
                            // Draw bent path
                            const midY = (startY + targetBottomY) / 2;
                            const evadeX = startX + (displayedW * 0.15); // bend right
                            routePath.setAttribute("d", `M ${startX} ${startY} Q ${evadeX} ${midY} ${targetCenterX} ${targetBottomY}`);
                            routePath.setAttribute("stroke", "#fca311");
                        } else {
                            // Draw straight path
                            routePath.setAttribute("d", `M ${startX} ${startY} L ${targetCenterX} ${targetBottomY}`);
                            routePath.setAttribute("stroke", "#00ffcc");
                        }
                    }
                }
            }

            function updateCollisionCounter(collisions) {
                if (collisions === undefined || collisions === null) return;
                
                // 1. Update windowed counter
                const cc = document.getElementById('collision-counter');
                if (cc) {
                    const currentCount = parseInt(cc.dataset.count || "0");
                    if (collisions > currentCount) {
                        logDebug(`<span style="color:#f44747">Collision Detected! Total: ${collisions}</span>`);
                    }
                    cc.textContent = `Collisions: ${collisions}`;
                    cc.dataset.count = collisions;
                }
                
                // 2. Update fullscreen counter
                const fsCc = document.getElementById('fs-collision-counter');
                if (fsCc) {
                    fsCc.textContent = `Collisions: ${collisions}`;
                    fsCc.dataset.count = collisions;
                }
            }

            async function sendMoveCommand(action) {
                const fd = new FormData();
                fd.append('command', action);
                try {
                    const res = await fetch('/move', { method: 'POST', body: fd });
                    const data = await res.json();
                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                        photoDisplay.style.display = 'block';
                        placeholder.style.display = 'none';

                        // SYNC UI State for Manual Tracking
                        if (data.state && currentAutomationMode === 'manual') {
                            switchCoTPromptTab(data.state.toLowerCase(), true, data);
                        }

                        if (data.collisions !== undefined) {
                            updateCollisionCounter(data.collisions);
                        }

                        // NEW: Special Auto-Start VLM Recovery on Manual Movement Collision
                        if (data.tracking_info && typeof data.tracking_info === 'string' && data.tracking_info.startsWith('START_RECOVERY')) {
                            if (habitatSubMode === 'autonomous') {
                                logDebug(`<span style="color:#f44747"><b>[System]</b> Collision detected in Autonomous VLM! Automatically transitioning to RECOVERING and starting CoT Analysis...</span>`);
                                
                                // Set initial-state dropdown input to start directly in RECOVERING
                                const stateInput = document.getElementById('autonav-initial-state');
                                if (stateInput) stateInput.value = 'RECOVERING';
                                
                                // Transition the prompt tab/badge to recovering
                                switchCoTPromptTab('recovering', true, data);
                                
                                // Change automation mode to auto
                                setAutomationMode('auto');
                                
                                // Automatically trigger autonomous stream!
                                if (!isStreaming) {
                                    toggleAutonomousStream();
                                }
                            }
                        }

                        // NEW: Update Visual Lock Boundaries from Tracking Feedback
                        if (data.tracking_info && lockBoundaries) {
                            if (data.tracking_info === "CLEARING") {
                                // Hide lines during clearing
                                const ov = document.getElementById('visual-lock-overlay');
                                if (ov) ov.style.display = 'none';
                            } else {
                                lockBoundaries.x_min = data.tracking_info.x_min;
                                lockBoundaries.x_max = data.tracking_info.x_max;
                                updateVisualLockOverlay();
                            }
                        }

                        // NEW: Update True 3D Polygon from projection info
                        if (window.true3DProjectionActive && data.projection_info) {
                            updateTrue3DOverlay(data.projection_info);
                        }
                    }
                } catch (e) { console.error("Move command error:", e); }
            }

            async function fetchInitialView() {
                try {
                    const res = await fetch('/get_view', { method: 'POST' });
                    const data = await res.json();
                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                        photoDisplay.style.display = 'block';
                        placeholder.style.display = 'none';
                        video.style.display = 'none';
                        // Ensure the action button is updated now that we have content
                        updateActionButton();
                    }
                } catch (e) { console.error("Failed to fetch initial view:", e); }
            }

            function handleFileSelect(input, type) {
                if (input.files && input.files[0]) {
                    const file = input.files[0];
                    const url = URL.createObjectURL(file);

                    placeholder.style.display = 'none';

                    if (type === 'image') {
                        photoDisplay.src = url;
                        photoDisplay.style.display = 'block';
                        video.style.display = 'none';
                        document.getElementById('photo-info').textContent = "Selected: " + file.name;
                        document.getElementById('photo-info').style.display = 'block';
                        currentSourceName = file.name;
                        updateActionButton();
                    } else if (type === 'video') {
                        video.src = url;
                        video.style.display = 'block';
                        photoDisplay.style.display = 'none';
                        document.getElementById('video-info').textContent = "Selected: " + file.name;
                        document.getElementById('video-info').style.display = 'block';
                        currentSourceName = file.name;
                        updateActionButton();
                    } else if (type === 'sim') {
                        currentSourceName = file.name;
                        const simInfo = document.getElementById('sim-info');
                        simInfo.textContent = "Selected Sim: " + file.name;
                        simInfo.style.display = 'block';
                        placeholder.textContent = `Connected to: ${file.name}`;
                        updateActionButton();

                        // Proactively try to initialize the sim on the backend
                        // Note: In a real scenario, we might need to upload the file first
                        // For now, we'll assume the backend can handle the name or we'll need to update /init_sim
                        initializeSim(file);
                    }
                }
            }

            function selectSim() {
                document.getElementById('sim-upload').click();
            }

            async function initializeSim(file) {
                logDebug(`Initializing simulator with ${file.name}...`);
                const formData = new FormData();
                formData.append('file', file);
                const dims = getSimDimensions();
                formData.append('width', dims.width);
                formData.append('height', dims.height);
                formData.append('hfov', angleSettings.hfov);

                try {
                    const res = await fetch('/init_sim', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        logDebug(`Simulator initialized successfully.`);
                        isSimLoaded = true;
                        updateActionButton();

                        // Apply the chosen screen mode (Fullscreen vs Windowed)
                        setScreenMode(simInitMode === 'fullscreen' ? 'fullscreen' : 'window', false);

                        if (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous') {
                            // fetchInitialView();
                            showMapSelection();
                        }
                    } else {
                        logDebug(`<span style="color:#f44747">Init Failed: ${data.message}</span>`);
                    }
                } catch (e) {
                    logDebug(`<span style="color:#f44747">Error: ${e}</span>`);
                }
            }

            function getSimDimensions() {
                if (simInitMode === 'fullscreen' || habitatSubMode !== 'autonomous') {
                    return { width: 1920, height: 1080 };
                }
                const container = document.querySelector('.video-container');
                return {
                    width: container.clientWidth || 1920,
                    height: container.clientHeight || 1080
                };
            }

            function updateActionButton() {
                // Only show button if we have content
                let hasContent = (currentMode === 'photo' && photoDisplay.src && photoDisplay.src !== window.location.href) ||
                    (currentMode === 'video' && video.src && video.src !== window.location.href) ||
                    (currentMode === 'habitat' && currentSourceName !== '');

                actionBtn.style.display = 'block';

                // Tab Management
                const tabHeader = document.getElementById('habitat-tab-header');
                const promptHeader = document.getElementById('prompt-settings-header');
                const tabBtnAuto = document.getElementById('tab-btn-auto');
                const tabBtnManual = document.getElementById('tab-btn-manual');

                const btnRestart = document.getElementById('btn-restart-habitat');

                if (currentMode === 'habitat') {
                    if (btnRestart) btnRestart.style.display = 'inline-block';
                    tabHeader.style.display = 'flex';
                    promptHeader.style.display = 'none';

                    if (habitatSubMode === 'autonomous' || habitatSubMode === 'live') {
                        tabBtnManual.style.display = 'none';
                        tabBtnAuto.style.display = 'inline-block';
                        if (activePromptTab !== 'auto') {
                            switchPromptTab('auto');
                            return; // return because switchPromptTab calls updateActionButton
                        }
                    } else if (habitatSubMode === 'live_one_shot') {
                        tabBtnManual.style.display = 'inline-block';
                        tabBtnAuto.style.display = 'none';
                        if (activePromptTab !== 'manual') {
                            switchPromptTab('manual');
                            return;
                        }
                    } else {
                        tabBtnManual.style.display = 'inline-block';
                        tabBtnAuto.style.display = 'inline-block';
                    }
                } else {
                    if (btnRestart) btnRestart.style.display = 'none';
                    tabHeader.style.display = 'none';
                    promptHeader.style.display = 'flex';
                    if (activePromptTab === 'auto') {
                        switchPromptTab('manual');
                        return;
                    }
                }

                if (currentMode === 'photo') {
                    actionBtn.textContent = "Analyze Photo";
                    actionBtn.style.backgroundColor = "rgba(0, 122, 204, 0.8)";
                    actionBtn.style.color = "white";
                } else if (currentMode === 'habitat') {
                    if (isStreaming) {
                        actionBtn.textContent = (activePromptTab === 'auto' || habitatSubMode === 'autonomous') ? "Stop Navigation" : "Stop Assistant";
                        actionBtn.style.backgroundColor = "rgba(204, 0, 0, 0.8)";
                        actionBtn.style.color = "white";
                    } else {
                        if (habitatSubMode === 'autonomous') {
                            actionBtn.textContent = "Start CoT Analysis";
                            actionBtn.style.backgroundColor = "rgba(230, 190, 0, 0.9)";
                            actionBtn.style.color = "black";
                        } else if (habitatSubMode === 'live_one_shot') {
                            actionBtn.textContent = "Start Sim Analysis";
                            actionBtn.style.backgroundColor = "rgba(0, 122, 204, 0.8)";
                            actionBtn.style.color = "white";
                        } else {
                            // Live Control (State Transition) or Initial State
                            actionBtn.textContent = (activePromptTab === 'auto') ? "Start CoT Analysis" : "Start Sim Analysis";
                            actionBtn.style.backgroundColor = "rgba(230, 190, 0, 0.9)";
                            actionBtn.style.color = "black";
                        }
                    }
                } else if (currentMode === 'video') {
                    if (isStreaming) {
                        if (video.paused) {
                            actionBtn.textContent = "Wait (Paused)";
                            actionBtn.style.backgroundColor = "rgba(230, 190, 0, 0.9)";
                            actionBtn.style.color = "black";
                        } else {
                            actionBtn.textContent = "Stop Analysis";
                            actionBtn.style.backgroundColor = "rgba(204, 0, 0, 0.8)";
                            actionBtn.style.color = "white";
                        }
                    } else {
                        actionBtn.textContent = "Start Video Analysis";
                        actionBtn.style.backgroundColor = "rgba(0, 152, 24, 0.8)";
                        actionBtn.style.color = "white";
                    }
                }

                // Dimmed when no content (checks)
                const fpsControl = document.getElementById('fps-control');
                const gridControl = document.getElementById('grid-checkbox-container');
                const angleGridControl = document.getElementById('angle-grid-checkbox-container');
                const heightControl = document.getElementById('height-checkbox-container');
                const memoryModeControl = document.getElementById('memory-mode-container');

                // Hide memory mode entirely if we are in 'photo' mode
                if (memoryModeControl) {
                    if (currentMode === 'photo') {
                        memoryModeControl.style.display = 'none';
                    } else {
                        memoryModeControl.style.display = 'flex';
                    }
                }

                // Show/Hide grid controls wrapper based on mode
                const gridWrapper = document.getElementById('grid-controls-wrapper');
                if (gridWrapper) {
                    gridWrapper.style.display = (currentMode === 'habitat') ? 'grid' : 'none';
                }

                // For Habitat Record mode, we need content (sim selected) AND we ignore isStreaming
                if (!hasContent) {
                    actionBtn.classList.add('btn-dimmed');
                    fpsControl.classList.add('btn-dimmed');
                    gridControl.classList.add('dimmed');
                    angleGridControl.classList.add('dimmed');
                    heightControl.classList.add('dimmed');
                    if (memoryModeControl) memoryModeControl.classList.add('btn-dimmed');

                    document.getElementById('grid-toggle-checkbox').disabled = true;
                    document.getElementById('angle-grid-checkbox').disabled = true;

                    const bboxCb = document.getElementById('bbox-toggle-checkbox');
                    const bboxCont = document.getElementById('bbox-checkbox-container');
                    const bboxLbl = document.getElementById('bbox-label');
                    if (bboxCb) {
                        bboxCb.disabled = true;
                        if (bboxCont) bboxCont.style.opacity = "0.5";
                        if (bboxLbl) bboxLbl.style.cursor = "not-allowed";
                    }

                    const memCb = document.getElementById('memory-toggle-checkbox');
                    const memCont = document.getElementById('memory-checkbox-container');
                    const memLbl = document.getElementById('memory-label');
                    if (memCb) {
                        memCb.disabled = true;
                        if (memCont) memCont.style.opacity = "0.5";
                        if (memLbl) memLbl.style.cursor = "not-allowed";
                    }

                    document.getElementById('height-toggle-checkbox').disabled = true;
                    const memModeCb = document.getElementById('memory-mode-checkbox');
                    if (memModeCb) memModeCb.disabled = true;
                } else {
                    actionBtn.classList.remove('btn-dimmed');
                    fpsControl.classList.remove('btn-dimmed');
                    gridControl.classList.remove('dimmed');
                    angleGridControl.classList.remove('dimmed');
                    heightControl.classList.remove('dimmed');

                    document.getElementById('grid-toggle-checkbox').disabled = false;
                    document.getElementById('angle-grid-checkbox').disabled = false;

                    const bboxCb = document.getElementById('bbox-toggle-checkbox');
                    const bboxCont = document.getElementById('bbox-checkbox-container');
                    const bboxLbl = document.getElementById('bbox-label');

                    // Specific logic for Bounding Box: Only enable if Sim is loaded
                    if (bboxCb) {
                        if (currentMode === 'habitat' && !isSimLoaded) {
                            bboxCb.disabled = true;
                            if (bboxCont) bboxCont.style.opacity = "0.5";
                            if (bboxLbl) bboxLbl.style.cursor = "not-allowed";
                        } else {
                            bboxCb.disabled = false;
                            if (bboxCont) bboxCont.style.opacity = "1";
                            if (bboxLbl) bboxLbl.style.cursor = "pointer";
                        }
                    }

                    const memCb = document.getElementById('memory-toggle-checkbox');
                    const memCont = document.getElementById('memory-checkbox-container');
                    const memLbl = document.getElementById('memory-label');
                    if (memCb) {
                        if (currentMode === 'habitat' && !isSimLoaded) {
                            memCb.disabled = true;
                            if (memCont) memCont.style.opacity = "0.5";
                            if (memLbl) memLbl.style.cursor = "not-allowed";
                        } else {
                            memCb.disabled = false;
                            if (memCont) memCont.style.opacity = "1";
                            if (memLbl) memLbl.style.cursor = "pointer";
                        }
                    }

                    document.getElementById('height-toggle-checkbox').disabled = false;

                    const isCustomPrompt = document.getElementById('use-custom-prompt').checked;
                    const memModeCb = document.getElementById('memory-mode-checkbox');

                    if (isCustomPrompt) {
                        if (memoryModeControl) memoryModeControl.classList.remove('btn-dimmed');
                        if (memModeCb) memModeCb.disabled = false;
                    } else {
                        if (memoryModeControl) memoryModeControl.classList.add('btn-dimmed');
                        if (memModeCb) memModeCb.disabled = true;
                    }
                }
            }

            function ensureTrue3DOverlayExists() {
                let svgOverlay = document.getElementById('true-3d-overlay');
                if (!svgOverlay) {
                    svgOverlay = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                    svgOverlay.id = 'true-3d-overlay';
                    svgOverlay.style.position = 'absolute';
                    svgOverlay.style.top = '0';
                    svgOverlay.style.left = '0';
                    svgOverlay.style.width = '100%';
                    svgOverlay.style.height = '100%';
                    svgOverlay.style.pointerEvents = 'none';
                    svgOverlay.style.zIndex = '200';

                    const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                    polygon.id = 'true-3d-polygon';
                    polygon.setAttribute("fill", "rgba(0, 255, 204, 0.2)");
                    polygon.setAttribute("stroke", "#00ffcc");
                    polygon.setAttribute("stroke-width", "3");
                    polygon.setAttribute("stroke-dasharray", "5,5");
                    svgOverlay.appendChild(polygon);
                    
                    const routePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
                    routePath.id = 'true-3d-route';
                    routePath.setAttribute("fill", "none");
                    routePath.setAttribute("stroke", "#00ffcc");
                    routePath.setAttribute("stroke-width", "5");
                    routePath.setAttribute("stroke-dasharray", "10,10");
                    routePath.setAttribute("style", "filter: drop-shadow(0px 0px 5px rgba(0, 255, 204, 0.8)); opacity: 0; transition: opacity 0.3s;");
                    svgOverlay.appendChild(routePath);

                    const container = document.querySelector('.video-container');
                    if (container) container.appendChild(svgOverlay);
                }
                svgOverlay.style.display = 'block';
                return svgOverlay;
            }

            async function activate3DProjection() {
                const samOverlay = document.getElementById('sam-box-overlay');
                const projBtn = document.getElementById('btn-3d-projection');

                if (window.true3DProjectionActive) {
                    // DEACTIVATE
                    window.true3DProjectionActive = false;
                    const svgOverlay = document.getElementById('true-3d-overlay');
                    if (svgOverlay) svgOverlay.style.display = 'none';
                    if (samOverlay && currentSAMBox) samOverlay.style.display = 'block';

                    projBtn.style.background = '';
                    projBtn.style.color = '';
                    projBtn.textContent = '3D Projection';

                    if (typeof logDebug === 'function') {
                        logDebug('<span style="color:#ce9178;">[System] True 3D Projection deactivated.</span>');
                    }
                    return;
                }

                if (samOverlay && currentSAMBox) {
                    try {
                        const response = await fetch('/start_3d_projection', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ bbox: currentSAMBox })
                        });
                        const data = await response.json();

                        if (data.status === 'success') {
                            window.true3DProjectionActive = true;
                            // Remove the old HTML-based 3D CSS effect
                            samOverlay.style.display = 'none';

                            // Let the system handle true 3D projection overlay
                            ensureTrue3DOverlayExists();

                            if (data.projection_info) {
                                updateTrue3DOverlay(data.projection_info);
                            }

                            // Simple animation for the 3D button
                            projBtn.style.background = '#00ffcc';
                            projBtn.style.color = 'black';
                            projBtn.textContent = '3D Active';
                            projBtn.disabled = false; // Ensure it stays enabled for toggle

                            if (typeof logDebug === 'function') {
                                logDebug('<span style="color:#00ffcc; font-weight:bold;">[System] True 3D Projection initialized.</span>');
                            }
                        } else {
                            alert("Failed to initialize 3D projection: " + data.message);
                        }
                    } catch (e) {
                        console.error("3D Projection error:", e);
                    }
                }
            }

            function toggleGrid() {
                const isChecked = document.getElementById('grid-toggle-checkbox').checked;
                const gridOverlay = document.getElementById('grid-overlay');
                gridOverlay.style.display = isChecked ? 'block' : 'none';
                if (isChecked) updateGridOverlay();
            }

            function toggleAngleGrid() {
                const isChecked = document.getElementById('angle-grid-checkbox').checked;
                const angleOverlay = document.getElementById('angle-grid-overlay');
                if (angleOverlay) angleOverlay.style.display = isChecked ? 'block' : 'none';

                // Update UI Indicator
                const indicator = document.getElementById('angle-grid-status-indicator');
                if (indicator) {
                    indicator.textContent = isChecked ? "Angle Grid: Active" : "Angle Grid: Passive";
                    indicator.style.color = isChecked ? "#4ec9b0" : "#f44747";
                }

                if (isChecked) {
                    generateAngleGrid();
                    updateGridOverlay();

                    // Mutual Exclusivity: Turn off Bounding Box
                    const bboxCb = document.getElementById('bbox-toggle-checkbox');
                    if (bboxCb && bboxCb.checked) {
                        bboxCb.checked = false;
                        toggleBoundingBox();
                    }

                    // Update Prompt to Angle Grid Template
                    const s = scenarios[currentScenario] || scenarios['scenario1'];
                    if (s) {
                        s.core = `[SYSTEM] Navigation Assistant.\n[VISION SYSTEM: ANGLE GRID]\n[GOAL] {goal}\n[RULES]\n1. Observation & Reasoning: MAX 1 short sentence each.\n\n[FORMAT]\nObservation: {goal} is at [X] degrees.\nReasoning: Found target.\n<cmd>COMMAND</cmd>`;
                        refreshPromptEditor();
                        syncScenariosToServer();
                    }
                }
            }

            function toggleBoundingBox() {
                const isChecked = document.getElementById('bbox-toggle-checkbox').checked;

                // Update UI Indicator
                const indicator = document.getElementById('bbox-status-indicator');
                if (indicator) {
                    indicator.textContent = isChecked ? "Bounding Box: Active" : "Bounding Box: Passive";
                    indicator.style.color = isChecked ? "#4ec9b0" : "#f44747";
                }

                if (isChecked) {
                    // Mutual Exclusivity: Turn off Angle Grid
                    const angleCb = document.getElementById('angle-grid-checkbox');
                    if (angleCb && angleCb.checked) {
                        angleCb.checked = false;
                        toggleAngleGrid();
                    }

                    // Update Prompt to Bounding Box Template
                    const s = scenarios[currentScenario] || scenarios['scenario1'];
                    if (s) {
                        s.core = `Task: {goal}.\nOutput: <box>(x1,y1),(x2,y2)</box>\n\nRule: ONLY output the bounding box. No descriptions.`;
                        refreshPromptEditor();
                        syncScenariosToServer();
                    }
                }
            }

            function refreshPromptEditor() {
                const editor = document.getElementById('autonav-prompt-editor');
                const s = scenarios[currentScenario] || scenarios['scenario1'];
                if (editor && s && (!currentPromptTab || currentPromptTab === 'core')) {
                    editor.value = s.core || "";
                }
            }

            function generateAngleGrid() {
                const overlay = document.getElementById('angle-grid-overlay');
                overlay.innerHTML = '';
                // 0 is center. Lines at 0, ±15, ±30, ±45 degrees (HFOV=90°).
                // Perspektif-doğru formül: tan(θ) / tan(HFOV/2)
                // HFOV/2 = 45° için tan(45°) = 1, yani: leftPercent = 50 + 50 * tan(θ)
                const halfFOVrad = (angleSettings.hfov / 2) * Math.PI / 180;
                const angles = angleSettings.angles;
                const op = angleSettings.opacity;
                angles.forEach(angle => {
                    const theta = angle * Math.PI / 180;
                    const leftPercent = 50 + 50 * Math.tan(theta) / Math.tan(halfFOVrad);

                    const line = document.createElement('div');
                    line.className = 'angle-line';
                    line.style.left = `${leftPercent}%`;
                    line.style.backgroundColor = `rgba(0, 255, 0, ${op})`;
                    overlay.appendChild(line);

                    const label = document.createElement('div');
                    label.className = 'angle-label';
                    label.style.left = `${leftPercent}%`;
                    label.style.top = '60px'; // Standardized with backend and processing
                    label.style.color = `rgba(0, 255, 0, ${op})`;
                    label.textContent = `${angle}°`;
                    overlay.appendChild(label);
                });
            }

            // ── Angle Settings ──────────────────────────────────────────────
            let angleSettings = {
                hfov: 90,
                angles: [-40, -30, -20, -10, 0, 10, 20, 30, 40],
                opacity: 0.8
            };

            function openAngleSettings() {
                document.getElementById('angle-settings-modal').style.display = 'flex';
                const currentLen = angleSettings.angles.length;
                setAngleMode(currentLen >= 7 ? '9' : '5');

                // Set FOV slider
                document.getElementById('fov-slider').value = angleSettings.hfov;
                document.getElementById('fov-display').textContent = angleSettings.hfov;
            }

            function setAngleMode(mode) {
                document.getElementById('as-mode-val').value = mode;
                document.getElementById('mode-9-btn').classList.toggle('active', mode === '9');
                document.getElementById('mode-5-btn').classList.toggle('active', mode === '5');
            }

            function closeAngleSettings() {
                document.getElementById('angle-settings-modal').style.display = 'none';
            }

            function saveAngleSettings() {
                const mode = document.getElementById('as-mode-val').value;
                const fov = parseInt(document.getElementById('fov-slider').value);

                let parsedAngles = [0];
                if (mode === '9') {
                    parsedAngles = [-40, -30, -20, -10, 0, 10, 20, 30, 40];
                } else {
                    parsedAngles = [-40, -20, 0, 20, 40];
                }

                angleSettings.angles = parsedAngles;
                angleSettings.hfov = fov;

                closeAngleSettings();

                // If simulator is loaded, we might need to re-init if FOV changes?
                // Actually, for now we just update the grid.
                // But the user said "attention to FOV", so maybe we SHOULD re-init.
                if (isSimLoaded && currentSourceName) {
                    logDebug(`FOV updated to ${fov}°. Re-initializing simulator...`);
                    // We need a way to re-init with same scene but new FOV.
                    // Let's assume loadScene can be called again.
                    loadScene(currentSourceName);
                }

                if (document.getElementById('angle-grid-checkbox').checked) {
                    generateAngleGrid();
                    updateGridOverlay();
                }
            }
            // ────────────────────────────────────────────────────────────────

            function updateGridOverlay() {
                const gridOverlay = document.getElementById('grid-overlay');
                const angleOverlay = document.getElementById('angle-grid-overlay');
                const is3x3Enabled = document.getElementById('grid-toggle-checkbox').checked;
                const isAngleEnabled = document.getElementById('angle-grid-checkbox').checked;

                if (!is3x3Enabled && !isAngleEnabled) {
                    if (gridOverlay) gridOverlay.style.display = 'none';
                    if (angleOverlay) angleOverlay.style.display = 'none';
                    return;
                }

                let activeEl = (currentMode === 'photo' || currentMode === 'habitat') ? photoDisplay : video;
                if (!activeEl || activeEl.offsetParent === null) return;

                const containerWidth = activeEl.clientWidth;
                const containerHeight = activeEl.clientHeight;

                let contentWidth, contentHeight;
                let left, top;

                // Always use contain logic to support both legacy and optimized modes without distortion
                let intrinsicWidth = (activeEl.tagName === 'IMG') ? activeEl.naturalWidth : activeEl.videoWidth;
                let intrinsicHeight = (activeEl.tagName === 'IMG') ? activeEl.naturalHeight : activeEl.videoHeight;

                if (!intrinsicWidth || !intrinsicHeight) {
                    intrinsicWidth = requestedSimWidth;
                    intrinsicHeight = requestedSimHeight;
                }

                const containerRatio = containerWidth / containerHeight;
                const contentRatio = intrinsicWidth / intrinsicHeight;
                const isFillMode = activeEl.style.objectFit === 'fill';

                if (isFillMode) {
                    contentWidth = containerWidth;
                    contentHeight = containerHeight;
                    left = 0;
                    top = 0;
                } else {
                    if (containerRatio > contentRatio) {
                        contentHeight = containerHeight;
                        contentWidth = containerHeight * contentRatio;
                    } else {
                        contentWidth = containerWidth;
                        contentHeight = containerWidth / contentRatio;
                    }
                    left = (containerWidth - contentWidth) / 2;
                    top = (containerHeight - contentHeight) / 2;
                }

                const commonStyles = {
                    width: `${contentWidth}px`,
                    height: `${contentHeight}px`,
                    left: `${activeEl.offsetLeft + left}px`,
                    top: `${activeEl.offsetTop + top}px`,
                    display: 'block'
                };

                if (is3x3Enabled) {
                    Object.assign(gridOverlay.style, commonStyles);
                } else {
                    gridOverlay.style.display = 'none';
                }

                if (isAngleEnabled) {
                    Object.assign(angleOverlay.style, commonStyles);
                } else {
                    angleOverlay.style.display = 'none';
                }

                updateVisualLockOverlay();
                updateSAMBoxOverlay();
            }

            let currentSAMBox = null;
            function updateSAMBoxOverlay() {
                const samOverlay = document.getElementById('sam-box-overlay');
                if (!samOverlay || !currentSAMBox) {
                    if (samOverlay) samOverlay.style.display = 'none';
                    return;
                }

                let activeEl = (currentMode === 'photo' || currentMode === 'habitat') ? photoDisplay : video;
                if (!activeEl || activeEl.offsetParent === null) return;

                const style = window.getComputedStyle(activeEl);
                const fit = style.objectFit;
                const containerWidth = activeEl.clientWidth;
                const containerHeight = activeEl.clientHeight;

                let contentWidth, contentHeight;
                let leftOffset, topOffset;

                // Always use contain logic to support both legacy and optimized modes without distortion
                let intrinsicWidth = (activeEl.tagName === 'IMG') ? activeEl.naturalWidth : activeEl.videoWidth;
                let intrinsicHeight = (activeEl.tagName === 'IMG') ? activeEl.naturalHeight : activeEl.videoHeight;
                if (!intrinsicWidth || !intrinsicHeight) {
                    intrinsicWidth = requestedSimWidth;
                    intrinsicHeight = requestedSimHeight;
                }

                const containerRatio = containerWidth / containerHeight;
                const contentRatio = intrinsicWidth / intrinsicHeight;
                const isFillMode = activeEl.style.objectFit === 'fill';

                if (isFillMode) {
                    contentWidth = containerWidth;
                    contentHeight = containerHeight;
                    leftOffset = 0;
                    topOffset = 0;
                } else {
                    if (containerRatio > contentRatio) {
                        contentHeight = containerHeight;
                        contentWidth = containerHeight * contentRatio;
                    } else {
                        contentWidth = containerWidth;
                        contentHeight = containerWidth / contentRatio;
                    }
                    leftOffset = (containerWidth - contentWidth) / 2;
                    topOffset = (containerHeight - contentHeight) / 2;
                }

                samOverlay.style.display = 'block';
                samOverlay.style.left = `${activeEl.offsetLeft + leftOffset + currentSAMBox.x_min * contentWidth}px`;
                samOverlay.style.top = `${activeEl.offsetTop + topOffset + currentSAMBox.y_min * contentHeight}px`;
                samOverlay.style.width = `${(currentSAMBox.x_max - currentSAMBox.x_min) * contentWidth}px`;
                samOverlay.style.height = `${(currentSAMBox.y_max - currentSAMBox.y_min) * contentHeight}px`;
            }

            function updateVisualLockOverlay() {
                const overlay = document.getElementById('visual-lock-overlay');
                if (!overlay || overlay.style.display === 'none' || !lockBoundaries) return;

                const activeEl = photoDisplay;
                if (!activeEl || activeEl.offsetParent === null) return;

                const containerWidth = activeEl.clientWidth;
                const containerHeight = activeEl.clientHeight;
                const intrinsicWidth = activeEl.naturalWidth || 640;
                const intrinsicHeight = activeEl.naturalHeight || 480;

                const containerRatio = containerWidth / containerHeight;
                const contentRatio = intrinsicWidth / intrinsicHeight;
                const isFillMode = activeEl.style.objectFit === 'fill';

                let contentWidth, contentHeight;
                let left, top;

                if (isFillMode) {
                    contentWidth = containerWidth;
                    contentHeight = containerHeight;
                    left = 0;
                    top = 0;
                } else {
                    if (containerRatio > contentRatio) {
                        contentHeight = containerHeight;
                        contentWidth = containerHeight * contentRatio;
                    } else {
                        contentWidth = containerWidth;
                        contentHeight = containerWidth / contentRatio;
                    }
                    left = (containerWidth - contentWidth) / 2;
                    top = (containerHeight - contentHeight) / 2;
                }

                overlay.style.width = `${contentWidth}px`;
                overlay.style.height = `${contentHeight}px`;
                overlay.style.left = `${activeEl.offsetLeft + left}px`;
                overlay.style.top = `${activeEl.offsetTop + top}px`;

                const lineL = document.getElementById('lock-line-left');
                const lineR = document.getElementById('lock-line-right');

                if (lineL && lineR) {
                    // Left line: hide if out of bounds
                    if (lockBoundaries.x_min < 0 || lockBoundaries.x_min > 1) {
                        lineL.style.display = 'none';
                    } else {
                        lineL.style.display = 'block';
                        lineL.style.left = (lockBoundaries.x_min * 100).toFixed(2) + '%';
                    }

                    // Right line: hide if out of bounds
                    if (lockBoundaries.x_max < 0 || lockBoundaries.x_max > 1) {
                        lineR.style.display = 'none';
                    } else {
                        lineR.style.display = 'block';
                        lineR.style.left = (lockBoundaries.x_max * 100).toFixed(2) + '%';
                    }
                }
            }

            window.addEventListener('resize', updateGridOverlay);
            video.addEventListener('loadedmetadata', updateGridOverlay);
            photoDisplay.addEventListener('load', updateGridOverlay);

            let currentHeightOffset = 0.0;
            let isHeightLocked = false;

            async function loadHeightSettings() {
                try {
                    const res = await fetch('/get_settings');
                    const data = await res.json();
                    currentHeightOffset = data.height || 0.0;
                    const checkbox = document.getElementById('height-toggle-checkbox');
                    // Always start UNCHECKED as requested
                    checkbox.checked = false;
                    updateHeightLabel();
                } catch (e) { }
            }

            function updateHeightLabel() {
                document.getElementById('height-label').textContent = `Height: ${currentHeightOffset.toFixed(1)}m`;
            }

            function toggleHeightControl() {
                const isChecked = document.getElementById('height-toggle-checkbox').checked;
                isHeightLocked = isChecked;
                saveHeightSettings();
            }

            let isUpdatingHeight = false;
            async function saveHeightSettings() {
                if (isUpdatingHeight) return;
                isUpdatingHeight = true;

                const formData = new FormData();
                formData.append('height', currentHeightOffset);
                formData.append('locked', document.getElementById('height-toggle-checkbox').checked);

                try {
                    const res = await fetch('/update_height', { method: 'POST', body: formData });
                    const data = await res.json();

                    if (data.status === 'success' && data.frame) {
                        photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                        photoDisplay.style.display = 'block';
                        placeholder.style.display = 'none';
                        updateGridOverlay();
                        console.log("Height updated visually:", data.message);
                    }
                } catch (e) {
                    console.error("Failed to update height:", e);
                } finally {
                    isUpdatingHeight = false;
                }
            }

            document.addEventListener('DOMContentLoaded', function () {
                loadHeightSettings();
            });

            async function getProcessedBlob(originalBlob) {
                const isGridEnabled = document.getElementById('grid-toggle-checkbox') && document.getElementById('grid-toggle-checkbox').checked;
                const isAngleGridEnabled = document.getElementById('angle-grid-checkbox') && document.getElementById('angle-grid-checkbox').checked;

                if (!isGridEnabled && !isAngleGridEnabled) return originalBlob;

                return new Promise((resolve) => {
                    const img = new Image();
                    img.onload = () => {
                        const canvas = document.createElement('canvas');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0);

                        if (isGridEnabled) {
                            // Draw 3x3 Grid
                            ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
                            ctx.lineWidth = 2; // Visible for VLM

                            // Vertical lines
                            ctx.beginPath();
                            ctx.moveTo(canvas.width / 3, 0); ctx.lineTo(canvas.width / 3, canvas.height);
                            ctx.moveTo(2 * canvas.width / 3, 0); ctx.lineTo(2 * canvas.width / 3, canvas.height);
                            // Horizontal lines
                            ctx.moveTo(0, canvas.height / 3); ctx.lineTo(canvas.width, canvas.height / 3);
                            ctx.moveTo(0, 2 * canvas.height / 3); ctx.lineTo(canvas.width, 2 * canvas.height / 3);
                            ctx.stroke();
                        }

                        if (isAngleGridEnabled) {
                            const halfFOVrad = (angleSettings.hfov / 2) * Math.PI / 180;
                            const angles = angleSettings.angles;
                            const op = angleSettings.opacity || 0.8;

                            ctx.strokeStyle = `rgba(0, 255, 0, ${op})`;
                            ctx.fillStyle = `rgba(0, 255, 0, ${op})`;

                            // Scale line width and font size aggressively so it survives the 448px server resize
                            // Minimalist lines for VLM
                            const dynLineWidth = 8;
                            ctx.lineWidth = dynLineWidth;

                            const dynFontSize = 60;
                            ctx.font = `bold ${dynFontSize}px Arial, sans-serif`;
                            ctx.textAlign = 'center';

                            angles.forEach(angle => {
                                const theta = angle * Math.PI / 180;
                                const leftPercent = 50 + 50 * Math.tan(theta) / Math.tan(halfFOVrad);
                                const x = canvas.width * (leftPercent / 100);

                                ctx.beginPath();
                                ctx.moveTo(x, 0);
                                ctx.lineTo(x, canvas.height);
                                ctx.stroke();

                                // Draw angle text with robust black outline for VLM
                                ctx.save();
                                const yPos = 60;
                                ctx.textBaseline = 'top';

                                // Stronger outline for canvas processing
                                ctx.strokeStyle = 'black';
                                ctx.lineWidth = 6;
                                ctx.strokeText(`${angle}°`, x, yPos);

                                ctx.fillStyle = `rgba(0, 255, 0, ${op})`;
                                ctx.fillText(`${angle}°`, x, yPos);
                                ctx.restore();
                            });
                        }

                        canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.9);
                    };
                    img.src = URL.createObjectURL(originalBlob);
                });
            }

            function handleAction() {
                if (currentMode === 'photo') {
                    analyzePhoto();
                } else if (currentMode === 'habitat' && (habitatSubMode === 'live' || habitatSubMode === 'live_one_shot' || habitatSubMode === 'autonomous')) {
                    if (habitatSubMode === 'live_one_shot') {
                        // Single analysis step for one-shot mode
                        triggerAnalysisStep();
                    } else if (activePromptTab === 'auto') {
                        if (currentAutomationMode === 'manual') {
                            analyzeSimSnapshot();
                        } else {
                            toggleAutonomousStream();
                        }
                    } else {
                        toggleStream();
                    }
                } else {
                    toggleStream();
                }
            }

            let autonavEventSource = null;
            let isAnalyzing = false; // LOCK to prevent overlapping requests

            window.cotStateInfo = {
                currentState: 'SEARCHING',
                searchingResult: '',
                bbox: null,
                projectionActive: false,
                navigatingLocation: '',
                recoveringMsg: '',
                history: []
            };

            function renderCotContent() {
                const cotContent = document.getElementById('cot-content');
                if (!cotContent) return;

                let html = '';

                // Draw History Items (completed past search cycles) first
                if (window.cotStateInfo.history && window.cotStateInfo.history.length > 0) {
                    window.cotStateInfo.history.forEach((h, index) => {
                        html += `<div style="font-size: 17px; font-weight: bold; color: #888; margin-bottom: 8px;">Reasoning (Scan ${index + 1}):</div>`;
                        html += `<div style="font-size: 16px; color: #aaa; margin-bottom: 6px; padding-left: 10px; border-left: 2px solid #555;">Is there a door? <span style="font-weight: bold; color: #e06c75;">No</span></div>`;
                        if (h.action) {
                            html += `<div style="font-size: 15px; color: #d19a66; font-style: italic; margin-bottom: 18px; padding-left: 10px; border-left: 2px solid #d19a66;">${h.action}</div>`;
                        }
                    });
                }

                const state = (window.cotStateInfo && window.cotStateInfo.currentState) ? window.cotStateInfo.currentState.toUpperCase() : 'SEARCHING';
                const scanIndex = (window.cotStateInfo.history ? window.cotStateInfo.history.length : 0) + 1;

                // Step 1: SEARCHING State (Current cycle foundation)
                html += `<div style="font-size: 19px; font-weight: bold; color: #4ec9b0; margin-bottom: 8px;">Reasoning${scanIndex > 1 ? ` (Scan ${scanIndex})` : ''}:</div>`;
                if (window.cotStateInfo.searchingResult) {
                    html += `<div style="font-size: 16px; color: #dcdcaa; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #4ec9b0;">Is there a door? <span style="font-weight: bold; color: ${window.cotStateInfo.searchingResult.toLowerCase() === 'yes' ? '#98c379' : '#e06c75'};">${window.cotStateInfo.searchingResult}</span></div>`;
                    
                    if (window.cotStateInfo.searchingResult.toLowerCase() === 'no') {
                        html += `<div style="font-size: 15px; color: #d19a66; font-style: italic; margin-bottom: 18px; padding-left: 10px; border-left: 2.5px solid #d19a66; animation: cot-pulse 1.5s infinite;">I must search environment. Turning 90 degrees...</div>`;
                    }
                } else {
                    html += `<div style="font-size: 16px; color: #888; display: flex; align-items: center; gap: 10px; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #d19a66;">Is there a door? <span class="cot-spinner" style="width: 14px; height: 14px; border-width: 2.5px;"></span></div>`;
                }

                // Step 2: FINDING State (Appends if we transitioned forward)
                const hasPassedSearching = (state === 'FINDING' || state === 'SCANNING_PATH' || state === 'NAVIGATING' || state === 'RECOVERING' || state === 'SUCCESS' || state === 'STOPPED');
                if (hasPassedSearching || window.cotStateInfo.bbox || window.cotStateInfo.projectionActive) {
                    html += `<div style="font-size: 16px; color: #4ec9b0; font-weight: bold; margin-bottom: 6px; padding-left: 10px; border-left: 2.5px solid #4ec9b0;">There is a door, Finding Threshold..</div>`;
                    
                    if (window.cotStateInfo.bbox) {
                        const b = window.cotStateInfo.bbox;
                        html += `<div style="font-size: 15px; font-family: monospace; color: #c586c0; margin-left: 18px; margin-bottom: 10px;">BBox: [${b.x_min.toFixed(2)}, ${b.y_min.toFixed(2)}, ${b.x_max.toFixed(2)}, ${b.y_max.toFixed(2)}]</div>`;
                    } else if (state === 'FINDING' && !window.cotStateInfo.projectionActive) {
                        html += `<div style="font-size: 15px; color: #888; display: flex; align-items: center; gap: 8px; margin-left: 18px; margin-bottom: 10px;">Locating bounding box... <span class="cot-spinner" style="width: 13px; height: 13px; border-width: 2px;"></span></div>`;
                    }

                    if (window.cotStateInfo.projectionActive) {
                        html += `<div style="font-size: 16px; color: #00ffcc; font-weight: bold; margin-left: 18px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#00ffcc; box-shadow: 0 0 8px #00ffcc; flex-shrink: 0;"></span>3D Projection active.</div>`;
                    } else if (state === 'FINDING' && window.cotStateInfo.bbox) {
                        html += `<div style="font-size: 15px; color: #888; display: flex; align-items: center; gap: 8px; margin-left: 18px; margin-bottom: 14px;">Activating 3D projection... <span class="cot-spinner" style="width: 13px; height: 13px; border-width: 2px;"></span></div>`;
                    }
                }

                // Step 2.5: SCANNING_PATH State
                const hasPassedScanning = (state === 'NAVIGATING' || state === 'RECOVERING' || state === 'SUCCESS' || state === 'STOPPED');
                if (state === 'SCANNING_PATH' || (hasPassedScanning && window.currentScenario === 'scenario2')) {
                    if (state === 'SCANNING_PATH') {
                        html += `<div style="font-size: 16px; color: #fca311; font-weight: bold; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #fca311; animation: cot-pulse 1.5s infinite;">Scanning floor for obstacles... <span class="cot-spinner" style="width: 14px; height: 14px; border-width: 2.5px; border-color: #fca311; border-right-color: transparent;"></span></div>`;
                    } else if (hasPassedScanning) {
                        html += `<div style="font-size: 15px; color: #888; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #fca311;">Path scanned and safe waypoint calculated.</div>`;
                    }
                }

                // Step 3: NAVIGATING State (Appends if navigated or complete)
                const hasPassedFinding = (state === 'NAVIGATING' || state === 'RECOVERING' || state === 'SUCCESS' || state === 'STOPPED');
                if (hasPassedFinding || window.cotStateInfo.navigatingLocation) {
                    let locStr = window.cotStateInfo.navigatingLocation;
                    if (locStr) {
                        html += `<div style="font-size: 16px; color: #98c379; font-weight: bold; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #98c379;">Moving through ${locStr} of projection</div>`;
                    } else if (state === 'NAVIGATING') {
                        html += `<div style="font-size: 16px; color: #888; display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #98c379;">Initializing servo control... <span class="cot-spinner" style="width: 14px; height: 14px; border-width: 2.5px;"></span></div>`;
                    }
                }

                // Step 4: RECOVERING State
                if (state === 'RECOVERING' || window.cotStateInfo.recoveringMsg) {
                    html += `<div style="font-size: 16px; color: #e06c75; font-weight: bold; margin-bottom: 14px; padding-left: 10px; border-left: 2.5px solid #e06c75; animation: cot-pulse 1.5s infinite;">Collision happened, recovering..</div>`;
                }

                // Step 5: Final status indicators
                if (state === 'SUCCESS') {
                    html += `<div style="font-size: 17px; color: #4ec9b0; font-weight: bold; text-align: center; margin-top: 18px; padding: 10px; border: 1.5px solid rgba(78, 201, 176, 0.45); border-radius: 8px; background: rgba(78, 201, 176, 0.12);">🏆 SUCCESS: Door passage completed.</div>`;
                } else if (state === 'STOPPED') {
                    html += `<div style="font-size: 16px; color: #e06c75; font-weight: bold; text-align: center; margin-top: 18px; padding: 8px; border: 1.5px solid rgba(224, 108, 117, 0.45); border-radius: 8px; background: rgba(224, 108, 117, 0.12);">Navigation Stopped.</div>`;
                }

                cotContent.innerHTML = html;
                
                // Ensure scroll updates smoothly and automatically so the latest content is always visible
                // Multiple passes ensure perfect bottom-sliding even with custom delayed rendering steps
                [50, 150, 300].forEach(delay => {
                    setTimeout(() => {
                        const cotOverlay = document.getElementById('cot-overlay');
                        if (cotOverlay) {
                            cotOverlay.scrollTo({
                                top: cotOverlay.scrollHeight,
                                behavior: 'smooth'
                            });
                        }
                    }, delay);
                });
            }

            async function toggleAutonomousStream() {
                const btn = document.getElementById('action-btn');
                const cotOverlay = document.getElementById('cot-overlay');
                const cotContent = document.getElementById('cot-content');

                if (isStreaming) {
                    // STOP
                    fetch('/stop_autonomous_navigate', { method: 'POST' });
                    if (autonavEventSource) {
                        autonavEventSource.close();
                        autonavEventSource = null;
                    }
                    isStreaming = false;
                    btn.textContent = (activePromptTab === 'auto' || habitatSubMode === 'autonomous') ? "Start CoT Analysis" : "Start CoT Assistant";
                    btn.style.backgroundColor = "rgba(230, 190, 0, 0.9)";
                    btn.style.color = "black";
                    cotOverlay.style.border = "1px solid #444";
                    document.getElementById('cot-state').textContent = "STOPPED";
                    document.getElementById('cot-state').style.backgroundColor = "#555";
                    updateFullscreenStatusLabel('INACTIVE');
                    
                    window.cotStateInfo.currentState = 'STOPPED';
                    renderCotContent();

                    // Reset initial state to SEARCHING when the stream stops or is completed
                    setInitialState('SEARCHING');
                } else {
                    // START
                    cotContent.innerHTML = '';
                    cotOverlay.style.display = 'block';
                    cotOverlay.style.border = "1px solid #007acc";
                    document.getElementById('cot-state').textContent = "RUNNING";
                    document.getElementById('cot-state').style.backgroundColor = "#007acc";
                    updateFullscreenStatusLabel('STARTED ANALYSING');
                    
                    window.cotStateInfo = {
                        currentState: document.getElementById('autonav-initial-state').value || 'SEARCHING',
                        searchingResult: '',
                        bbox: null,
                        projectionActive: false,
                        navigatingLocation: '',
                        recoveringMsg: '',
                        history: []
                    };
                    renderCotContent();

                    // Reset collision counters in UI immediately upon starting ONLY if not starting in RECOVERING state
                    const initState = document.getElementById('autonav-initial-state').value;
                    if (initState !== 'RECOVERING') {
                        updateCollisionCounter(0);
                    }

                    const formData = new FormData();
                    formData.append('goal', document.getElementById('autonav-target').value);
                    formData.append('initial_state', document.getElementById('autonav-initial-state').value);
                    formData.append('device_choice', selectedDevice);
                    formData.append('execute_cmds', "true"); // Continuous Auto mode always executes commands
                    if (selectedModel) formData.append('model_choice', selectedModel);
                    formData.append('is_fullscreen', document.body.classList.contains('fullscreen-active'));
                    formData.append('scenario', currentScenario);

                    // Send prompts for CURRENT scenario
                    const s = scenarios[currentScenario] || scenarios['scenario1'];
                    formData.append('core_prompt', s.core);
                    formData.append('searching_prompt', s.searching || "");
                    formData.append('finding_prompt', s.finding || "");
                    formData.append('navigating_prompt', s.navigating || "");
                    formData.append('stopping_prompt', s.stopping || "");
                    formData.append('recovering_prompt', s.recovering || "");

                    btn.disabled = true;
                    btn.textContent = "Starting...";

                    try {
                        const startRes = await fetch('/start_autonomous_navigate', {
                            method: 'POST', body: formData
                        });
                        const startData = await startRes.json();
                        if (startData.status !== 'success') {
                            alert("Could not start: " + startData.message);
                            btn.disabled = false;
                            cotOverlay.style.display = 'none';
                            return;
                        }

                        isStreaming = true;
                        btn.disabled = false;
                        btn.textContent = (activePromptTab === 'auto' || habitatSubMode === 'autonomous') ? "Stop CoT Analysis" : "Stop Assistant";
                        btn.style.backgroundColor = "rgba(204, 0, 0, 0.8)";
                        btn.style.color = "white";

                        logDebug("Starting AutonomousNavigator Stream...");

                        let currentStepResultDiv = null;
                        autonavEventSource = new EventSource('/autonomous_navigate_stream');

                        autonavEventSource.onmessage = function (event) {
                            try {
                                const data = JSON.parse(event.data);
                                if (data.type === 'log') {
                                    logDebug(`[AutoNav] ${data.data}`);
                                    if (data.data.toLowerCase().includes('3d projection active')) {
                                        window.cotStateInfo.projectionActive = true;
                                        renderCotContent();
                                    }
                                } else if (data.type === 'reasoning_chunk') {
                                    updateFullscreenStatusLabel('IN ACTION');

                                    // Parse for SEARCHING result
                                    if (window.cotStateInfo.currentState === 'SEARCHING') {
                                        if (data.data.toLowerCase().includes('yes')) {
                                            window.cotStateInfo.searchingResult = 'Yes';
                                            renderCotContent();
                                        } else if (data.data.toLowerCase().includes('no')) {
                                            window.cotStateInfo.searchingResult = 'No';
                                            renderCotContent();
                                        }
                                    }

                                    // 2. Update Main Result Display (Real-time stream)
                                    if (!currentStepResultDiv) {
                                        const timestamp = new Date().toLocaleTimeString();
                                        const entryId = 'prompt-' + Date.now();
                                        const wrapper = document.createElement('div');
                                        wrapper.className = "analysis-wrapper";
                                        wrapper.style.margin = "8px 0";
                                        wrapper.style.border = "1px solid #444";
                                        wrapper.style.borderRadius = "8px";
                                        wrapper.style.background = "#252526";

                                        const promptBtn = window.lastAutonomousPrompt ? `
                                            <button onclick="const p = document.getElementById('${entryId}'); p.style.display = p.style.display === 'none' ? 'block' : 'none'; this.textContent = p.style.display === 'none' ? 'Show Full Prompt' : 'Hide Full Prompt';" 
                                                style="background: #333; color: #ccc; border: 1px solid #555; padding: 4px 10px; font-size: 11px; border-radius: 4px; cursor: pointer; float: right; margin-top: -5px; font-weight: bold;">Show Full Prompt</button>
                                        ` : "";

                                        const promptBlock = window.lastAutonomousPrompt ? `
                                            <div id="${entryId}" style="display: none; background: #000; color: #858585; padding: 10px; font-family: 'Consolas', monospace; font-size: 11px; border-bottom: 1px solid #333; white-space: pre-wrap; max-height: 150px; overflow-y: auto;">${window.lastAutonomousPrompt}</div>
                                        ` : "";

                                        wrapper.innerHTML = `
                                            <div style="background: #1e1e1e; padding: 10px 20px; border-bottom: 1px solid #444; font-size: 13px; color: #4ec9b0; display: flex; justify-content: space-between; align-items: center;">
                                                <span>AUTONOMOUS ANALYSIS STEP [${timestamp}]</span>
                                                ${promptBtn}
                                            </div>
                                            ${promptBlock}
                                            <div class="step-content" style="padding: 15px; border-left: 6px solid #e6a822; font-size: 17px; line-height: 1.6; white-space: pre-wrap; color: #ddd;"></div>
                                        `;
                                        resultDisplay.appendChild(wrapper);
                                        currentStepResultDiv = wrapper.querySelector('.step-content');
                                    }

                                    // Clean tags for display but keep basic structure
                                    const chunk = data.data.replace(/<br>/g, '\n').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
                                    currentStepResultDiv.innerHTML += chunk + " ";
                                } else if (data.type === 'state_update') {
                                    const stateEl = document.getElementById('cot-state');
                                    const state = data.data.state.toUpperCase();
                                    stateEl.textContent = state;

                                    // Dynamic Styling for Top Badge
                                    if (state === 'SEARCHING') stateEl.style.backgroundColor = '#d19a66';
                                    else if (state === 'FINDING') stateEl.style.backgroundColor = '#4ec9b0';
                                    else if (state === 'SCANNING_PATH') stateEl.style.backgroundColor = '#fca311';
                                    else if (state === 'NAVIGATING') stateEl.style.backgroundColor = '#98c379';
                                    else if (state === 'STOPPING') stateEl.style.backgroundColor = '#e06c75';
                                    else if (state === 'RECOVERING') stateEl.style.backgroundColor = '#d19a66'; // Recovery also orange-ish or similar to searching

                                    // Update CoT State Info
                                    if (state === 'SEARCHING' && window.cotStateInfo.searchingResult === 'No') {
                                        // Move current search-and-turn step to history chain
                                        window.cotStateInfo.history.push({
                                            type: 'search',
                                            searchingResult: 'No',
                                            action: 'I must search environment. Turning 90 degrees...',
                                            completed: true
                                        });
                                        window.cotStateInfo.searchingResult = '';
                                        window.cotStateInfo.bbox = null;
                                        window.cotStateInfo.projectionActive = false;
                                        window.cotStateInfo.navigatingLocation = '';
                                        window.cotStateInfo.recoveringMsg = '';
                                    }

                                    window.cotStateInfo.currentState = state;
                                    if (state === 'FINDING') {
                                        window.cotStateInfo.bbox = null;
                                        window.cotStateInfo.projectionActive = false;
                                    } else if (state === 'SEARCHING' && window.cotStateInfo.searchingResult !== 'No') {
                                        window.cotStateInfo.searchingResult = '';
                                    } else if (state === 'RECOVERING') {
                                        window.cotStateInfo.recoveringMsg = 'recovering';
                                    }
                                    renderCotContent();

                                    // Reset current step div for the next iteration in Result Display
                                    currentStepResultDiv = null;

                                    // SYNC UI: Update pills and prompt tab
                                    const stateKey = state.toLowerCase();
                                    switchCoTPromptTab(stateKey, true); // Update pills/nodes without saving
                                } else if (data.type === 'error') {
                                    logDebug(`<span style="color:#f44747">[AutoNav Error] ${data.data}</span>`);
                                } else if (data.type === 'frame_update') {
                                    // Received a base64 frame update or a dict with projection_info
                                    const frameData = data.data;
                                    if (typeof frameData === 'string') {
                                        photoDisplay.src = "data:image/jpeg;base64," + frameData;
                                    } else if (frameData && frameData.frame) {
                                        photoDisplay.src = "data:image/jpeg;base64," + frameData.frame;
                                        // PERSISTENCE: Update True 3D Polygon if active
                                        if (frameData.projection_info) {
                                            // Force active if we receive projection data in autonomous mode
                                            window.true3DProjectionActive = true;
                                            ensureTrue3DOverlayExists();
                                            updateTrue3DOverlay(frameData.projection_info);

                                            // Extract corners and calculate visual center projection location
                                            const corners = frameData.projection_info.corners;
                                            if (corners && corners.length > 0) {
                                                const validCorners = corners.filter(c => !c.behind);
                                                if (validCorners.length > 0) {
                                                    const xs = validCorners.map(c => c.x);
                                                    const ys = validCorners.map(c => c.y);
                                                    const center_x = xs.reduce((a, b) => a + b, 0) / xs.length;
                                                    const center_y = ys.reduce((a, b) => a + b, 0) / ys.length;
                                                    window.cotStateInfo.navigatingLocation = `(X: ${center_x.toFixed(2)}, Y: ${center_y.toFixed(2)})`;
                                                }
                                            }
                                            window.cotStateInfo.projectionActive = true;
                                            renderCotContent();
                                        }
                                        if (frameData.collisions !== undefined) {
                                            updateCollisionCounter(frameData.collisions);
                                        }
                                    }
                                    updateGridOverlay();
                                } else if (data.type === 'sam_update') {
                                    currentSAMBox = data.data.box;
                                    updateSAMBoxOverlay();
                                    
                                    if (data.data.box) {
                                        window.cotStateInfo.bbox = data.data.box;
                                        renderCotContent();
                                    }

                                    const projBtn = document.getElementById('btn-3d-projection');
                                    if (projBtn) {
                                        projBtn.disabled = false;
                                        projBtn.style.opacity = '1';
                                        projBtn.style.cursor = 'pointer';
                                        projBtn.style.background = 'rgba(255,165,0,0.8)';
                                        projBtn.style.color = 'white';
                                    }
                                } else if (data.type === 'route_update') {
                                    const routePath = document.getElementById('true-3d-route');
                                    if (routePath) {
                                        routePath.setAttribute("data-status", data.data.status);
                                        routePath.style.opacity = "1";
                                        
                                        // Auto-hide after 5 seconds to keep screen clean
                                        setTimeout(() => {
                                            if (routePath) routePath.style.opacity = "0";
                                        }, 5000);
                                    }
                                } else if (data.type === 'prompt_update') {
                                    window.lastAutonomousPrompt = data.data;
                                } else if (data.type === 'success') {
                                    logDebug(`<span style="color:#4ec9b0; font-size: 18px; font-weight: bold;">🏆 SUCCESS: ${data.data}</span>`);
                                    const resultDisplay = document.getElementById('result-display');
                                    resultDisplay.innerHTML += `
                                        <div style="background: rgba(78, 201, 176, 0.2); border: 2px solid #4ec9b0; color: #4ec9b0; padding: 20px; border-radius: 8px; margin-top: 20px; text-align: center; font-size: 20px; font-weight: bold;">
                                            🎉 MISSION ACCOMPLISHED: DOORWAY PASSED!
                                        </div>
                                    `;
                                    resultDisplay.scrollTop = resultDisplay.scrollHeight;
                                    updateFullscreenStatusLabel('END');

                                    window.cotStateInfo.currentState = 'SUCCESS';
                                    renderCotContent();
                                } else if (data.type === 'stopped') {
                                    toggleAutonomousStream(); // Triggers the stop block
                                    window.true3DProjectionActive = false;
                                    const svgOverlay = document.getElementById('true-3d-overlay');
                                    if (svgOverlay) svgOverlay.style.display = 'none';

                                    const showPromptBtn = document.getElementById('btn-show-auto-prompt');
                                    if (showPromptBtn) showPromptBtn.style.display = 'none';
                                    const autoPromptBlock = document.getElementById('auto-prompt-block');
                                    if (autoPromptBlock) autoPromptBlock.style.display = 'none';

                                    const projBtn = document.getElementById('btn-3d-projection');
                                    if (projBtn) {
                                        projBtn.disabled = true;
                                        projBtn.style.opacity = '0.5';
                                        projBtn.style.cursor = 'not-allowed';
                                        projBtn.style.background = 'rgba(255,165,0,0.1)';
                                        projBtn.style.color = '#888';
                                        projBtn.textContent = '3D Projection';
                                    }

                                    window.cotStateInfo.currentState = 'STOPPED';
                                    renderCotContent();
                                }
                                cotOverlay.scrollTop = cotOverlay.scrollHeight;
                            } catch (e) {
                                console.error("Parse Error in SSE:", e);
                            }
                        };

                        autonavEventSource.onerror = function () {
                            if (isStreaming) {
                                toggleAutonomousStream();
                                logDebug(`<span style="color:#f44747">[AutoNav] Stream disconnected.</span>`);
                            }
                        }

                    } catch (e) {
                        alert("Error starting stream: " + e);
                        btn.disabled = false;
                    }
                }
            }

            async function analyzeSimSnapshot() {
                if (currentMode !== 'habitat') return;

                // PhotoDisplay holds the current base64 frame from simulator
                const base64Data = photoDisplay.src.split(',')[1];
                if (!base64Data) {
                    logDebug(`<span style="color:#f44747">Error: No frame to analyze.</span>`);
                    return;
                }

                // Convert base64 to Blob
                const byteCharacters = atob(base64Data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const originalBlob = new Blob([byteArray], { type: 'image/jpeg' });

                logDebug("Capturing simulator snapshot for analysis...");

                const blobToSend = await getProcessedBlob(originalBlob);

                // Send to backend asynchronously without awaiting so UI doesn't freeze
                sendFileToBackend(blobToSend).catch(e => {
                    console.error("Async analysis error:", e);
                    logDebug(`<span style="color:#f44747">Async Error: ${e}</span>`);
                });
            }



            function togglePromptInput() {
                const isCustom = document.getElementById('use-custom-prompt').checked;
                if (isCustom) {
                    promptInput.disabled = false;
                    promptInput.classList.add('active');
                    if (!promptInput.value || promptInput.value === BASE_PROMPT) {
                        promptInput.focus();
                    }
                } else {
                    promptInput.disabled = true;
                    promptInput.classList.remove('active');
                    promptInput.value = BASE_PROMPT; // Always revert to base
                }
                updateButtonStates();
            }

            async function savePrompt() {
                const content = promptInput.value;
                const name = prompt("Enter a name for this prompt (will be saved in /core prompts):");
                if (name) {
                    const formData = new FormData();
                    formData.append('name', name);
                    formData.append('content', content);

                    try {
                        const res = await fetch('/save_prompt', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await res.json();
                        alert(data.message);
                    } catch (e) {
                        alert("Error saving prompt: " + e);
                    }
                }
            }

            function loadPromptFromFile(input) {
                const file = input.files[0];
                if (!file) return;

                const reader = new FileReader();
                reader.onload = function (e) {
                    const content = e.target.result;
                    promptInput.value = content;

                    // Enable custom prompt mode
                    const checkbox = document.getElementById('use-custom-prompt');
                    checkbox.checked = true;
                    togglePromptInput();

                    // Reset file input so same file can be loaded again if desired
                    input.value = '';
                };
                reader.readAsText(file);
            }

            function updateFPS(val) {
                captureIntervalSec = val;
                fpsLabel.textContent = val;
                if (isStreaming) {
                    stopStream();
                    startStream();
                }
            }

            async function captureFrameFromVideo() {
                if (currentMode === 'habitat') {
                    // PhotoDisplay holds the current base64 frame from simulator
                    const base64Data = photoDisplay.src.split(',')[1];
                    if (base64Data) {
                        const byteCharacters = atob(base64Data);
                        const byteNumbers = new Array(byteCharacters.length);
                        for (let i = 0; i < byteCharacters.length; i++) {
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }
                        const byteArray = new Uint8Array(byteNumbers);
                        return new Blob([byteArray], { type: 'image/jpeg' });
                    }
                }
                const context = canvas.getContext('2d');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));
            }

            function getCurrentPrompt() {
                const isCustom = document.getElementById('use-custom-prompt').checked;
                let promptText = "";

                if (activePromptTab === 'auto') {
                    // If in OptiSight tab, merge Core + State prompts
                    const scenario = scenarios[currentScenario] || scenarios['scenario1'];
                    const corePart = scenario.core || "";

                    const editor = document.getElementById('autonav-prompt-editor');
                    if (!currentPromptTab && currentAutomationMode === 'manual') {
                        promptText = corePart; // Fallback to Core prompt if no state is selected
                    } else {
                        const statePart = editor.value;

                        // Prepend core IF state is not 'searching' or 'core'
                        // Searching prompt is a standalone Yes/No question now.
                        if (currentPromptTab === 'core' || currentPromptTab === 'searching') {
                            promptText = statePart;
                        } else {
                            promptText = corePart + "\n\n" + statePart;
                        }
                    }
                } else if (isCustom) {
                    promptText = promptInput.value;
                } else {
                    promptText = BASE_PROMPT;
                }

                // Ensure Angle Grid Instructions are appended if Angle Grid is active, EXCEPT in auto tab where toggleAngleGrid already handles modifying the scenario.core
                const isAngleGridChecked = document.getElementById('angle-grid-checkbox') && document.getElementById('angle-grid-checkbox').checked;

                if (isAngleGridChecked && activePromptTab !== 'auto') {
                    const angleGridInstructions = `\n[VISION SYSTEM: ANGLE GRID]\n- Use green lines to find {goal} degree.\n- Labels: -40 to +40. 0 is center.\n- Format: <cmd>Turn X Degrees Left/Right</cmd> or <cmd>Go Ahead</cmd>.\n`;
                    if (!promptText.includes("[VISION SYSTEM: ANGLE GRID]")) {
                        if (promptText.includes("=== NOW ANALYZE THE GIVEN IMAGE ===")) {
                            promptText = promptText.replace("=== NOW ANALYZE THE GIVEN IMAGE ===", angleGridInstructions + "\n=== NOW ANALYZE THE GIVEN IMAGE ===");
                        } else {
                            promptText += "\n" + angleGridInstructions + "\n\n=== NOW ANALYZE THE GIVEN IMAGE ===\nOutput:\n";
                        }
                    }
                }

                return promptText;
            }

            function logDebug(message) {
                const timestamp = new Date().toLocaleTimeString();
                const logEntry = `<div style="margin-bottom: 5px; border-bottom: 1px solid #333; padding-bottom: 5px;"><span style="color:#569cd6">[${timestamp}]</span> <span style="color:#4ec9b0">DEBUG:</span> ${message}</div>`;
                resultDisplay.insertAdjacentHTML('beforeend', logEntry); // Append
                scrollToBottom();
            }

            let lastResult = null;
            let lastPrompt = null;
            let lastMetadata = null;
            let lastAngleInfo = null; // Store last detected bbox for visual servo
            let lastDebugLog = '';

            async function restartHabitat() {
                if (!confirm("Are you sure you want to reset simulation memory and restart view?")) return;

                stopStream();
                if (currentAnalysisController) currentAnalysisController.abort();

                const cotContent = document.getElementById('cot-content');
                if (cotContent) cotContent.innerHTML = '';

                // Reset local result state
                lastResult = null;
                lastPrompt = null;
                lastMetadata = null;
                lastDebugLog = '';
                updateButtonStates();

                resultDisplay.innerHTML = 'Restarting...';

                try {
                    const res = await fetch('/clear_habitat_memory', { method: 'POST' });
                    const data = await res.json();
                    if (data.status === 'success') {
                        logDebug("Memory cleared. Current view and position preserved.");
                        resultDisplay.innerHTML = 'Waiting for input...';
                    } else {
                        alert("Error: " + data.message);
                    }
                } catch (e) {
                    console.error("Restart error:", e);
                    alert("Restart failed: " + e);
                }
            }

            function clearResult() {
                if (!confirm("Are you sure you want to clear the results?")) return;

                resultDisplay.innerHTML = 'Waiting for input...';
                lastResult = null;
                lastPrompt = null;
                lastMetadata = null;
                lastDebugLog = '';
                updateButtonStates();
            }

            function updateButtonStates() {
                const resultEmpty = resultDisplay.textContent.trim() === 'Waiting for input...' || resultDisplay.textContent.trim() === '';
                const promptEmpty = !promptInput.value || promptInput.value.trim() === '';
                const isCustomPrompt = document.getElementById('use-custom-prompt').checked;

                // Clear button
                const clearBtn = document.getElementById('btn-clear-result');
                clearBtn.classList.remove('btn-dimmed');

                // Save Result button
                const saveResultBtn = document.getElementById('btn-save-result');
                if (resultEmpty) {
                    saveResultBtn.classList.add('btn-dimmed');
                } else {
                    saveResultBtn.classList.remove('btn-dimmed');
                }

                // Save Prompt button
                const savePromptBtn = document.getElementById('btn-save-prompt');
                if (promptEmpty || !isCustomPrompt) {
                    savePromptBtn.classList.add('btn-dimmed');
                } else {
                    savePromptBtn.classList.remove('btn-dimmed');
                }

                // Load Prompt button
                const loadPromptBtn = document.getElementById('btn-load-prompt');
                if (!isCustomPrompt) {
                    loadPromptBtn.classList.add('btn-dimmed');
                } else {
                    loadPromptBtn.classList.remove('btn-dimmed');
                }

                // Memory Mode
                const memModeContainer = document.getElementById('memory-mode-container');
                const memModeCheckbox = document.getElementById('memory-mode-checkbox');
                if (!isCustomPrompt) {
                    if (memModeContainer) memModeContainer.classList.add('btn-dimmed');
                    if (memModeCheckbox) memModeCheckbox.disabled = true;
                } else {
                    // We let updateActionButton handle the final 'hasContent' disable logic
                    // but at a baseline, it's enabled here if custom prompt is on
                    if (memModeContainer) memModeContainer.classList.remove('btn-dimmed');
                    if (memModeCheckbox) memModeCheckbox.disabled = false;

                    // Re-apply content check if it exists so we don't accidentally enable it when we shouldn't
                    if (typeof updateActionButton === 'function') {
                        // Slight delay or direct check - but action button relies on globals so it's safe to just call
                        updateActionButton();
                    }
                }
            }

            async function saveCurrentResult() {
                if (!lastResult) return;
                const name = prompt("Enter a name for this result (will be saved in /results):");
                if (!name) return;
                const formData = new FormData();
                formData.append('name', name);
                formData.append('prompt', lastPrompt);
                formData.append('content', lastResult);
                formData.append('metadata', JSON.stringify(lastMetadata));
                formData.append('debug_log', lastDebugLog);
                formData.append('source_type', currentMode);
                formData.append('source_name', currentSourceName || 'Unknown');

                try {
                    const res = await fetch('/save_result', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    alert(data.message);
                } catch (e) {
                    alert("Error saving result: " + e);
                }
            }

            async function sendFileToBackend(fileBlob) {
                if (!fileBlob) return;
                if (isAnalyzing) {
                    console.log("[Lock] Analysis already in progress. Skipping duplicate request.");
                    return;
                }
                isAnalyzing = true;
                const actionBtn = document.getElementById('action-btn');
                if (actionBtn) actionBtn.disabled = true;

                const formData = new FormData();
                formData.append('file', fileBlob, 'image.jpg');
                formData.append('prompt', getCurrentPrompt());
                formData.append('goal', document.getElementById('autonav-target').value);
                formData.append('device_choice', selectedDevice);

                // Append Memory Mode choice
                const isMemoryModeEnabled = document.getElementById('memory-toggle-checkbox').checked;
                formData.append('memory_mode', isMemoryModeEnabled);

                if (selectedModel) {
                    formData.append('model_choice', selectedModel);
                }
                if (currentMode === 'habitat') {
                    formData.append('habitat_submode', habitatSubMode);
                    const isBboxEnabled = document.getElementById('bbox-toggle-checkbox').checked;
                    formData.append('bbox_mode', isBboxEnabled);
                    const isAngleGridEnabled = document.getElementById('angle-grid-checkbox').checked;
                    formData.append('angle_grid_mode', isAngleGridEnabled);
                }
                formData.append('is_fullscreen', document.body.classList.contains('fullscreen-active'));

                // Track state for memory history
                const promptState = currentPromptTab ? currentPromptTab.toUpperCase() : "CORE";
                formData.append('state', promptState);

                const finalPromptSent = getCurrentPrompt();
                formData.append('prompt', finalPromptSent);

                console.log(`[Frontend] Sending Analyze Request: State=${promptState}, Model=${selectedModel}`);
                logDebug(`Starting analysis [State: ${promptState}, Device: ${selectedDevice}]...`);
                console.log("Final Prompt Sent to VLM:", finalPromptSent);

                // Check if there's an existing controller (e.g. from same mode double-click? though buttons usually disabled/hidden or logic prevents. But safe to replace). 
                // Actually user logic said "tab switch". But cancelling previous on new start is also good practice.
                if (currentAnalysisController) currentAnalysisController.abort();
                currentAnalysisController = new AbortController();
                const signal = currentAnalysisController.signal;

                try {
                    const startTime = Date.now();
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        body: formData,
                        signal: signal
                    });

                    if (!response.ok) {
                        const errText = await response.text();
                        throw new Error(`Server returned ${response.status}: ${errText}`);
                    }

                    const data = await response.json();
                    const totalDuration = ((Date.now() - startTime) / 1000).toFixed(2);

                    if (data.response.startsWith("Error")) {
                        logDebug(`<span style="color:#f44747">FAILED: ${data.response}</span>`);
                    } else {
                        const loadTime = data.debug?.load_time || "0s";
                        const infTime = data.debug?.inference_time || "0s";

                        logDebug(`<span style="color:#dcdcaa">SUCCESS: Total ${totalDuration}s (Load: ${loadTime}, Inf: ${infTime})</span>`);

                        lastResult = data.response;
                        lastPrompt = getCurrentPrompt();
                        lastMetadata = data.debug;
                        lastAngleInfo = data.angle_info; // Store for visual servo
                        lastDebugLog = resultDisplay.innerText;
                        updateButtonStates();

                        // Handle Grounded-SAM Overlay
                        if (data.grounded_sam_active && data.angle_info && data.angle_info.box) {
                            currentSAMBox = data.angle_info.box;
                            updateSAMBoxOverlay();
                            const projBtn = document.getElementById('btn-3d-projection');
                            if (projBtn) {
                                projBtn.disabled = false;
                                projBtn.style.opacity = '1';
                                projBtn.style.cursor = 'pointer';
                                projBtn.style.background = 'rgba(255,165,0,0.8)';
                                projBtn.style.color = 'white';
                            }
                        } else {
                            currentSAMBox = null;
                            updateSAMBoxOverlay();
                            const projBtn = document.getElementById('btn-3d-projection');
                            if (projBtn) {
                                projBtn.disabled = true;
                                projBtn.style.opacity = '0.5';
                                projBtn.style.cursor = 'not-allowed';
                                projBtn.style.background = 'rgba(255,165,0,0.1)';
                                projBtn.style.color = '#888';
                                projBtn.textContent = '3D Projection';
                            }
                        }

                        const timestamp = new Date().toLocaleTimeString();
                        const mainResponse = data.response || "";

                        // Handle automatic state transitions from backend
                        if (data.next_state) {
                            const prevState = currentPromptTab;
                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Transitioning state to: ${data.next_state}</span>`);
                            switchCoTPromptTab(data.next_state.toLowerCase());

                            // AUTO-TRIGGER: If transitioning from SEARCHING to FINDING in Live mode,
                            // automatically trigger a one-shot Grounded-SAM analysis.
                            if (habitatSubMode === 'live' && prevState === 'searching' && data.next_state.toLowerCase() === 'finding') {
                                logDebug(`<span style="color:#ce9178"><b>[Auto-Nav]</b> Triggering one-shot Grounded-SAM analysis automatically...</span>`);

                                setTimeout(() => {
                                    // Ensure we are still in finding state before triggering
                                    if (currentPromptTab === 'finding') {
                                        analyzeSimSnapshot();
                                    }
                                }, 1500);
                            }
                        }

                        // NEW: Update photoDisplay if backend returned a new frame (e.g. after a search turn)
                        if (data.frame) {
                            photoDisplay.src = "data:image/jpeg;base64," + data.frame;
                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> View updated visually (Manual Auto-Move).</span>`);
                        }

                        // AUTO-SEARCH: If in SEARCHING and result is NO, trigger next step after turn delay
                        const isGoalNotFound = /(Goal_Check:\s*NO|^NO$|\nNO$)/i.test(mainResponse.trim());
                        if (currentPromptTab === 'searching' && isGoalNotFound) {
                            logDebug(`<span style="color:#ce9178"><b>[Auto-Search]</b> Goal not found. Automatically rotating and re-analyzing in 2s...</span>`);
                            setTimeout(() => {
                                if (currentPromptTab === 'searching' && currentAutomationMode === 'manual') {
                                    analyzeSimSnapshot();
                                }
                            }, 2000); // Reduced to 2s for better responsiveness
                        }

                        // Extract Memory block if present
                        let memoryBlockHTML = "";

                        const isMemoryOn = document.getElementById('memory-toggle-checkbox').checked;
                        const injectedMemory = data.injected_memory || "None";

                        if (isMemoryOn) {
                            // Escape the memory text
                            const escapedMemory = injectedMemory
                                .replace(/&/g, "&amp;")
                                .replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;");

                            memoryBlockHTML = `
                                <div style="background: #2b2b2b; padding: 15px; border-left: 6px solid #e6a822; margin: 0; border-bottom: 2px dashed #444;">
                                    <div style="color:#e6a822; font-weight:bold; font-size: 16px; margin-bottom:8px; text-transform: uppercase;">[Context] Memory Injected:</div>
                                    <div style="font-size: 16px; line-height: 1.5; color: #ddd; white-space: pre-wrap; font-family: 'Consolas', monospace;">${escapedMemory}</div>
                                </div>
                            `;
                        } else {
                            memoryBlockHTML = `
                                <div style="background: #1a1a1a; padding: 10px 15px; border-left: 6px solid #555; margin: 0; border-bottom: 2px dashed #333;">
                                    <div style="color:#888; font-weight:bold; font-size: 14px; text-transform: uppercase;">[Context] Memory: <span style="color: #f44747;">DEACTIVATED</span></div>
                                </div>
                            `;
                        }

                        // Escape HTML characters for the main response so tags like <cmd> are displayed as text
                        const escapedResponse = mainResponse
                            .replace(/&/g, "&amp;")
                            .replace(/</g, "&lt;")
                            .replace(/>/g, "&gt;");



                        // NEW: Bounding Box Angle Info Display
                        let angleBadgeHTML = "";
                        if (data.angle_info) {
                            const angleVal = data.angle_info.angle !== undefined ? data.angle_info.angle : "N/A";
                            const rangeVal = data.angle_info.range || "Unknown";
                            const boxData = data.angle_info.box;

                            angleBadgeHTML = `
                            <div style="background: rgba(78, 201, 176, 0.1); border: 1px dashed #4ec9b0; padding: 12px 15px; margin-top: 15px; border-radius: 6px; display: flex; flex-direction: column; gap: 8px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="background: #4ec9b0; color: #1e1e1e; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 12px; text-transform: uppercase;">Spatial Analysis</div>
                                    <div style="font-size: 16px; color: #4ec9b0; font-weight: bold;">Calculated Angle: ${angleVal}°</div>
                                </div>
                                <div style="font-size: 14px; color: #aaa;">
                                    <b>Range:</b> <span style="color: #ce9178;">${rangeVal}</span>
                                </div>
                                ${boxData ? `
                                <div style="font-size: 13px; color: #888; border-top: 1px solid #333; padding-top: 5px; margin-top: 5px;">
                                    <b>BBox:</b> [${boxData.x_min.toFixed(3)}, ${boxData.y_min.toFixed(3)}] to [${boxData.x_max.toFixed(3)}, ${boxData.y_max.toFixed(3)}]
                                </div>` : ""}
                            </div>
                            `;
                        }

                        // Enhanced CoT Header
                        let cotHeaderHTML = "";
                        const showPromptBtn = `
                            <div style="display: flex; gap: 10px;">
                                <button onclick="const p = this.parentElement.parentElement.nextElementSibling; p.style.display = p.style.display === 'none' ? 'block' : 'none';" 
                                    style="background: #333; color: #ccc; border: 1px solid #555; padding: 4px 10px; font-size: 12px; border-radius: 4px; cursor: pointer;">Show Full Prompt</button>
                            </div>`;

                        const promptBlock = `<div style="display: none; background: #000; color: #858585; padding: 15px; font-family: 'Consolas', monospace; font-size: 12px; border-bottom: 1px solid #333; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">${data.debug?.final_prompt || "Prompt not returned"}</div>`;

                        if (activePromptTab === 'auto') {
                            cotHeaderHTML = `
                            <div style="background: #1e1e1e; padding: 12px 20px; border-bottom: 1px solid #444; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
                                <div style="font-size: 14px; color: #ddd;">
                                    <span style="color: #4ec9b0; font-weight: bold; text-transform: uppercase;">Scenario:</span> ${currentScenario.toUpperCase()} | 
                                    <span style="color: #ce9178; font-weight: bold; text-transform: uppercase;">Progress:</span> ${promptState}
                                </div>
                                ${showPromptBtn}
                            </div>
                            ${promptBlock}
                        `;
                        } else {
                            // Fallback header for non-auto tabs to ensure prompt is accessible
                            cotHeaderHTML = `
                            <div style="background: #1e1e1e; padding: 8px 15px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
                                <div style="font-size: 12px; color: #888;">Analysis Context</div>
                                ${showPromptBtn}
                            </div>
                            ${promptBlock}
                            `;
                        }

                        let systemInfoHTML = "";
                        if (data.system_info) {
                            systemInfoHTML = `
                                <div class="system-info-box">
                                    <i class="fas fa-microchip"></i>
                                    <span><b>SYSTEM:</b> ${data.system_info}</span>
                                </div>
                            `;
                        }

                        let finalResult = "";
                        const ramGpuHTML = data.grounded_sam_active ? "" : `
                                <div style="display:flex; justify-content:space-between;">
                                    <span>RAM: <span style="color:white;">${data.debug?.ram_usage}</span></span>
                                    <span>GPU: <span style="color:white;">${data.debug?.gpu_usage}</span></span>
                                </div>`;

                        const debugTimingHTML = `
                            <div style="border-top: 1px solid #555; padding-top: 12px; font-size: 16px; font-family: 'Consolas', monospace; color: #aaa;">
                                <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                                    <span style="color: #4ec9b0; font-weight: bold;">Model: ${data.debug?.model_choice || 'Unknown'} | Device: ${data.debug?.device || 'Unknown'}</span>
                                    <span>Load: <span style="color:white;">${loadTime}</span> | Inf: <span style="color:white;">${infTime}</span></span>
                                </div>
                                <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                                    <span>Total Time: <span style="color:white;">${data.debug?.total_time}</span></span>
                                </div>
                                ${ramGpuHTML}
                            </div>
                        `;

                        if (resultDisplay.textContent.includes('Waiting for input...')) {
                            resultDisplay.innerHTML = '';
                        }

                        // Reconstruct a cleaner, more robust result block
                        finalResult = `
                            <div style="margin: 15px 0; border: 1px solid #444; border-radius: 8px; overflow: hidden; background: #252526; font-family: 'Consolas', monospace;">
                                ${cotHeaderHTML}
                                ${memoryBlockHTML}
                                <div style="padding: 20px; border-left: 6px solid ${data.grounded_sam_active ? '#c586c0' : '#007acc'};">
                                    <div style="color:${data.grounded_sam_active ? '#c586c0' : '#569cd6'}; font-weight:bold; font-size: 18px; margin-bottom:12px; border-bottom: 1px solid #444; padding-bottom: 5px;">
                                        [${timestamp}] ${data.grounded_sam_active ? 'GROUNDED-SAM OUTPUT' : 'VLM RAW OUTPUT'}
                                    </div>
                                    <div style="margin-bottom:15px; font-size: 17px; line-height: 1.6; white-space: pre-wrap; color: #dcdcaa;">${escapedResponse}</div>
                                    
                                    ${angleBadgeHTML}
                                    ${systemInfoHTML}
                                    
                                    <div style="margin-top:20px; padding-top: 10px; border-top: 1px dashed #444;">
                                        ${debugTimingHTML}
                                    </div>
                                </div>
                            </div>
                        `;
                        resultDisplay.insertAdjacentHTML('beforeend', finalResult);
                        scrollToBottom();

                        // Also show debug timing at the very bottom for easy visibility
                        const debugSummary = `<div style="margin-top: 5px; padding: 5px 10px; background: #1e1e1e; border-left: 3px solid #4ec9b0; font-family: 'Consolas', monospace; font-size: 14px; color: #888;">DEBUG: SUCCESS: Total ${totalDuration}s (Load: ${loadTime}, Inf: ${infTime})</div>`;
                        resultDisplay.insertAdjacentHTML('beforeend', debugSummary);
                        scrollToBottom();

                        // Automatic state transition to NAVIGATING removed to enforce manual gating.
                        // The system will still transition to FINDING via the backend's next_state if a goal is spotted.


                        // DELEGATED SEARCH TURN (Moved to end to ensure results are displayed first)
                        if (data.system_info === 'START_SEARCH_TURN') {
                            logDebug(`<span style="color:#ce9178"><b>[System]</b> Initiating smooth 90-degree search rotation...</span>`);

                            for (let i = 0; i < 9; i++) {
                                const fd_scan = new FormData();
                                fd_scan.append('command', 'turn_right');
                                const res_scan = await fetch('/move', { method: 'POST', body: fd_scan });
                                const data_scan = await res_scan.json();

                                if (data_scan.frame) {
                                    photoDisplay.src = "data:image/jpeg;base64," + data_scan.frame;
                                }
                                // Reduced delay to 300ms for slightly faster but visible rotation
                                await new Promise(r => setTimeout(r, 300));
                            }

                            logDebug(`<span style="color:#4ec9b0"><b>[System]</b> Scan complete. Re-analyzing...</span>`);
                            setTimeout(() => {
                                if (currentPromptTab === 'searching' && currentAutomationMode === 'manual') {
                                    analyzeSimSnapshot();
                                }
                            }, 1000);
                        }
                    }

                } catch (error) {
                    if (error.name === 'AbortError') {
                        console.log("Fetch aborted.");
                    } else {
                        console.error("Error details:", error);
                        logDebug(`<span style="color:#f44747">ERROR: ${error.message || 'Communication problem'}</span>`);
                    }
                } finally {
                    currentAnalysisController = null;
                    isAnalyzing = false;
                    const actionBtn = document.getElementById('action-btn');
                    if (actionBtn) actionBtn.disabled = false;
                }
            }

            async function analyzePhoto() {
                if (photoUpload.files && photoUpload.files[0]) {
                    const blobToSend = await getProcessedBlob(photoUpload.files[0]);
                    await sendFileToBackend(blobToSend);
                }
            }

            function toggleStream() {
                if (isStreaming) {
                    stopStream();
                } else {
                    startStream();
                }
                updateActionButton();
            }

            function startStream() {
                isStreaming = true;
                if (video.paused && currentMode === 'video') video.play();

                console.log(`Starting stream analysis...`);
                remainingTimeAtPause = 0;
                scheduleNextAnalysis(0);
            }

            function stopStream() {
                isStreaming = false;
                cancelCurrentAnalysis(); // For total stop, we do cancel pending
                if (streamTimeout) {
                    clearTimeout(streamTimeout);
                    streamTimeout = null;
                }
                if (currentMode === 'video') video.pause();

                window.true3DProjectionActive = false;
                const svgOverlay = document.getElementById('true-3d-overlay');
                if (svgOverlay) svgOverlay.style.display = 'none';

                const projBtn = document.getElementById('btn-3d-projection');
                if (projBtn) {
                    projBtn.disabled = true;
                    projBtn.style.opacity = '0.5';
                    projBtn.style.cursor = 'not-allowed';
                    projBtn.style.background = 'rgba(255,165,0,0.1)';
                    projBtn.style.color = '#888';
                    projBtn.textContent = '3D Projection';
                }
            }

            function scheduleNextAnalysis(delay) {
                if (streamTimeout) clearTimeout(streamTimeout);
                streamTimeout = setTimeout(triggerAnalysisStep, delay);
            }

            async function triggerAnalysisStep() {
                if (!isStreaming && habitatSubMode !== 'live_one_shot') return;
                if (currentMode === 'video' && video.paused) return;

                lastAnalysisTimestamp = Date.now();
                const originalBlob = await captureFrameFromVideo();
                const blobToSend = await getProcessedBlob(originalBlob);
                await sendFileToBackend(blobToSend);

                // Schedule next if still active and not paused
                if (isStreaming && (currentMode !== 'video' || !video.paused) && habitatSubMode !== 'live_one_shot') {
                    scheduleNextAnalysis(captureIntervalSec * 1000);
                }
            }

            // Initialize Default Mode
            setMode('photo');
            togglePromptInput(); // Set initial state of prompt input

            // Listen for prompt changes
            promptInput.addEventListener('input', updateButtonStates);

            // Initial state check
            updateButtonStates();
            loadScenariosFromServer();

            // Stop/Pause analysis based on video state
            video.addEventListener('ended', () => {
                if (isStreaming && currentMode === 'video') {
                    console.log("Video ended, stopping analysis.");
                    stopStream();
                    updateActionButton();
                }
            });

            video.addEventListener('pause', () => {
                if (isStreaming && currentMode === 'video') {
                    // Calculate remaining time
                    const elapsed = Date.now() - lastAnalysisTimestamp;
                    remainingTimeAtPause = (captureIntervalSec * 1000) - elapsed;
                    if (remainingTimeAtPause < 0) remainingTimeAtPause = 0;

                    console.log(`Video paused. Remaining time for next analysis: ${remainingTimeAtPause}ms`);

                    if (streamTimeout) {
                        clearTimeout(streamTimeout);
                        streamTimeout = null;
                    }
                    updateActionButton();
                    // Note: We do NOT cancelCurrentAnalysis() here so the last one can finish
                }
            });

            video.addEventListener('play', () => {
                if (isStreaming && currentMode === 'video' && !streamTimeout) {
                    console.log(`Video resumed. Rescheduling analysis in ${remainingTimeAtPause}ms`);
                    scheduleNextAnalysis(remainingTimeAtPause);
                    updateActionButton();
                }
            });

            function toggleAutoPromptDisplay() {
                const p = document.getElementById('auto-prompt-block');
                const btn = document.getElementById('btn-show-auto-prompt');
                if (!p) return;
                if (p.style.display === 'none') {
                    p.style.display = 'block';
                    btn.textContent = 'Hide Full Prompt';
                } else {
                    p.style.display = 'none';
                    btn.textContent = 'Show Full Prompt';
                }
            }

            async function takePanelScreenshot() {
                const actionBtn = document.getElementById('btn-take-screenshot');
                const originalText = actionBtn.innerHTML;
                
                if (typeof logDebug === 'function') logDebug("[Snapshot] Capture process started...");
                
                actionBtn.disabled = true;
                actionBtn.style.opacity = '0.7';
                actionBtn.innerHTML = "Capturing...";

                try {
                    const activeEl = (currentMode === 'photo' || currentMode === 'habitat') ? photoDisplay : video;
                    if (!activeEl || activeEl.offsetParent === null) {
                         alert("Error: Sim view is not visible or active.");
                         resetBtn(actionBtn, originalText);
                         return;
                    }

                    const canvas = document.createElement('canvas');
                    const w = activeEl.clientWidth;
                    const h = activeEl.clientHeight;
                    
                    if (w === 0 || h === 0) {
                        alert("Error: Simulator display size is 0x0.");
                        resetBtn(actionBtn, originalText);
                        return;
                    }

                    canvas.width = w;
                    canvas.height = h;
                    const ctx = canvas.getContext('2d');
                    
                    // 1. Draw Image
                    ctx.drawImage(activeEl, 0, 0, w, h);
                    if (typeof logDebug === 'function') logDebug(`[Snapshot] Background drawn (${w}x${h})`);

                    // 2. Draw 3x3 Grid
                    const gridOverlay = document.getElementById('grid-overlay');
                    if (gridOverlay && gridOverlay.style.display !== 'none') {
                        ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(w/3, 0); ctx.lineTo(w/3, h);
                        ctx.moveTo(2*w/3, 0); ctx.lineTo(2*w/3, h);
                        ctx.moveTo(0, h/3); ctx.lineTo(w, h/3);
                        ctx.moveTo(0, 2*h/3); ctx.lineTo(w, 2*h/3);
                        ctx.stroke();
                        if (typeof logDebug === 'function') logDebug("[Snapshot] 3x3 Grid drawn");
                    }

                    // 3. Draw Angle Grid
                    const angleGridOverlay = document.getElementById('angle-grid-overlay');
                    if (angleGridOverlay && angleGridOverlay.style.display !== 'none') {
                        const labels = angleGridOverlay.querySelectorAll('.angle-label');
                        labels.forEach(label => {
                            const left = parseFloat(label.style.left);
                            const x = (left / 100) * w;
                            ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
                            ctx.lineWidth = 4;
                            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
                            ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
                            ctx.font = 'bold 24px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText(label.textContent, x, 40);
                        });
                        if (typeof logDebug === 'function') logDebug("[Snapshot] Angle Grid drawn");
                    }

                    // 4. Draw SAM Box
                    const samOverlay = document.getElementById('sam-box-overlay');
                    if (samOverlay && samOverlay.style.display !== 'none') {
                        const rect = samOverlay.getBoundingClientRect();
                        const containerRect = activeEl.getBoundingClientRect();
                        const rx = rect.left - containerRect.left;
                        const ry = rect.top - containerRect.top;
                        const rw = rect.width;
                        const rh = rect.height;
                        ctx.strokeStyle = '#ff00ff';
                        ctx.lineWidth = 3;
                        ctx.strokeRect(rx, ry, rw, rh);
                        ctx.fillStyle = '#ff00ff';
                        ctx.fillRect(rx, ry - 25, 160, 25);
                        ctx.fillStyle = 'white';
                        ctx.font = 'bold 11px Arial';
                        ctx.textAlign = 'left';
                        ctx.fillText("SAM 2.1: door threshold", rx + 8, ry - 8);
                        if (typeof logDebug === 'function') logDebug("[Snapshot] SAM Box drawn");
                    }

                    // 5. Draw 3D Projection
                    const svgOverlay = document.getElementById('true-3d-overlay');
                    const polygon = document.getElementById('true-3d-polygon');
                    if (svgOverlay && svgOverlay.style.display !== 'none' && polygon) {
                        const pointsStr = polygon.getAttribute('points');
                        if (pointsStr) {
                            const points = pointsStr.trim().split(/\s+/).map(p => {
                                const [px, py] = p.split(',').map(parseFloat);
                                return { x: px, y: py };
                            });
                            if (points.length >= 3) {
                                ctx.strokeStyle = '#00ffcc';
                                ctx.lineWidth = 3;
                                ctx.fillStyle = 'rgba(0, 255, 204, 0.2)';
                                ctx.beginPath();
                                ctx.moveTo(points[0].x, points[0].y);
                                for(let i=1; i<points.length; i++) ctx.lineTo(points[i].x, points[i].y);
                                ctx.closePath();
                                ctx.fill(); ctx.stroke();
                                if (typeof logDebug === 'function') logDebug("[Snapshot] 3D Projection drawn");
                            }
                        }
                    }

                    // 6. Upload
                    actionBtn.innerHTML = "Uploading...";
                    const dataURL = canvas.toDataURL('image/jpeg', 0.9);
                    const res = await fetch('/save_screenshot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: dataURL })
                    });
                    const data = await res.json();
                    
                    if (data.status === 'success') {
                        if (typeof logDebug === 'function') {
                            logDebug(`<span style="color:#4ec9b0; font-weight:bold;">[Snapshot] SUCCESS: Saved as ${data.filename}</span>`);
                        }
                        actionBtn.innerHTML = "Saved!";
                    } else {
                        throw new Error(data.message || "Unknown backend error");
                    }
                    
                    setTimeout(() => resetBtn(actionBtn, originalText), 2000);

                } catch (e) {
                    console.error("Screenshot error:", e);
                    if (typeof logDebug === 'function') logDebug(`<span style="color:#f44747">[Snapshot] ERROR: ${e.message}</span>`);
                    alert("Screenshot failed: " + e.message);
                    resetBtn(actionBtn, originalText);
                }
            }

            function resetBtn(btn, text) {
                btn.innerHTML = text;
                btn.disabled = false;
                btn.style.opacity = '1';
            }

            async function takeFullscreenScreenshot() {
                const actionBtn = document.getElementById('btn-take-screenshot-fs');
                const originalText = actionBtn.innerHTML;
                
                if (typeof logDebug === 'function') logDebug("[Snapshot-FS] Fullscreen capture process started...");
                
                actionBtn.disabled = true;
                actionBtn.style.opacity = '0.7';
                actionBtn.innerHTML = "Capturing...";

                try {
                    const activeEl = (currentMode === 'photo' || currentMode === 'habitat') ? photoDisplay : video;
                    if (!activeEl || activeEl.offsetParent === null) {
                         alert("Error: Sim view is not visible or active.");
                         resetBtn(actionBtn, originalText);
                         return;
                    }

                    const canvas = document.createElement('canvas');
                    const w = activeEl.clientWidth;
                    const h = activeEl.clientHeight;
                    
                    if (w === 0 || h === 0) {
                        alert("Error: Simulator display size is 0x0.");
                        resetBtn(actionBtn, originalText);
                        return;
                    }

                    canvas.width = w;
                    canvas.height = h;
                    const ctx = canvas.getContext('2d');
                    
                    // 1. Draw Image
                    ctx.drawImage(activeEl, 0, 0, w, h);
                    if (typeof logDebug === 'function') logDebug(`[Snapshot-FS] Background drawn (${w}x${h})`);

                    // 2. Draw 3x3 Grid
                    const gridOverlay = document.getElementById('grid-overlay');
                    if (gridOverlay && gridOverlay.style.display !== 'none') {
                        ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(w/3, 0); ctx.lineTo(w/3, h);
                        ctx.moveTo(2*w/3, 0); ctx.lineTo(2*w/3, h);
                        ctx.moveTo(0, h/3); ctx.lineTo(w, h/3);
                        ctx.moveTo(0, 2*h/3); ctx.lineTo(w, 2*h/3);
                        ctx.stroke();
                        if (typeof logDebug === 'function') logDebug("[Snapshot-FS] 3x3 Grid drawn");
                    }

                    // 3. Draw Angle Grid
                    const angleGridOverlay = document.getElementById('angle-grid-overlay');
                    if (angleGridOverlay && angleGridOverlay.style.display !== 'none') {
                        const labels = angleGridOverlay.querySelectorAll('.angle-label');
                        labels.forEach(label => {
                            const left = parseFloat(label.style.left);
                            const x = (left / 100) * w;
                            ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
                            ctx.lineWidth = 4;
                            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
                            ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
                            ctx.font = 'bold 24px Arial';
                            ctx.textAlign = 'center';
                            ctx.fillText(label.textContent, x, 40);
                        });
                        if (typeof logDebug === 'function') logDebug("[Snapshot-FS] Angle Grid drawn");
                    }

                    // 4. Draw SAM Box
                    const samOverlay = document.getElementById('sam-box-overlay');
                    if (samOverlay && samOverlay.style.display !== 'none') {
                        const rect = samOverlay.getBoundingClientRect();
                        const containerRect = activeEl.getBoundingClientRect();
                        const rx = rect.left - containerRect.left;
                        const ry = rect.top - containerRect.top;
                        const rw = rect.width;
                        const rh = rect.height;
                        ctx.strokeStyle = '#ff00ff';
                        ctx.lineWidth = 3;
                        ctx.strokeRect(rx, ry, rw, rh);
                        ctx.fillStyle = '#ff00ff';
                        ctx.fillRect(rx, ry - 25, 160, 25);
                        ctx.fillStyle = 'white';
                        ctx.font = 'bold 11px Arial';
                        ctx.textAlign = 'left';
                        ctx.fillText("SAM 2.1: door threshold", rx + 8, ry - 8);
                        if (typeof logDebug === 'function') logDebug("[Snapshot-FS] SAM Box drawn");
                    }

                    // 5. Draw 3D Projection
                    const svgOverlay = document.getElementById('true-3d-overlay');
                    const polygon = document.getElementById('true-3d-polygon');
                    if (svgOverlay && svgOverlay.style.display !== 'none' && polygon) {
                        const pointsStr = polygon.getAttribute('points');
                        if (pointsStr) {
                            const points = pointsStr.trim().split(/\s+/).map(p => {
                                const [px, py] = p.split(',').map(parseFloat);
                                return { x: px, y: py };
                            });
                            if (points.length >= 3) {
                                ctx.strokeStyle = '#00ffcc';
                                ctx.lineWidth = 3;
                                ctx.fillStyle = 'rgba(0, 255, 204, 0.2)';
                                ctx.beginPath();
                                ctx.moveTo(points[0].x, points[0].y);
                                for(let i=1; i<points.length; i++) ctx.lineTo(points[i].x, points[i].y);
                                ctx.closePath();
                                ctx.fill(); ctx.stroke();
                                if (typeof logDebug === 'function') logDebug("[Snapshot-FS] 3D Projection drawn");
                            }
                        }
                    }

                    // 6. Draw Thinking Box (CoT Overlay)
                    const cotOverlay = document.getElementById('cot-overlay');
                    if (cotOverlay && cotOverlay.style.display !== 'none') {
                        const boxWidth = 440;
                        const boxLeft = 15;
                        const boxTop = 15;
                        
                        const cotContent = document.getElementById('cot-content');
                        const contentText = cotContent ? cotContent.innerText : '';
                        
                        ctx.font = "14px Consolas, Monaco, monospace";
                        const maxWidth = boxWidth - 48;
                        const lines = [];
                        const rawLines = contentText.split('\n');
                        
                        rawLines.forEach(rawLine => {
                            let currentLine = '';
                            const words = rawLine.split(' ');
                            for (let n = 0; n < words.length; n++) {
                                const testLine = currentLine + (currentLine ? ' ' : '') + words[n];
                                const metrics = ctx.measureText(testLine);
                                if (metrics.width > maxWidth && n > 0) {
                                    lines.push(currentLine);
                                    currentLine = words[n];
                                } else {
                                    currentLine = testLine;
                                }
                            }
                            lines.push(currentLine);
                        });
                        
                        const headerHeight = 64;
                        const lineHeight = 20;
                        const contentHeight = lines.length * lineHeight;
                        const boxHeight = headerHeight + contentHeight + 24;
                        
                        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
                        ctx.shadowBlur = 20;
                        ctx.shadowOffsetX = 0;
                        ctx.shadowOffsetY = 10;
                        
                        ctx.fillStyle = 'rgba(15, 15, 20, 0.93)';
                        ctx.strokeStyle = '#007acc';
                        ctx.lineWidth = 2;
                        
                        const r = 14;
                        const x = boxLeft;
                        const y = boxTop;
                        const w = boxWidth;
                        const h = boxHeight;
                        
                        ctx.beginPath();
                        ctx.moveTo(x + r, y);
                        ctx.lineTo(x + w - r, y);
                        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
                        ctx.lineTo(x + w, y + h - r);
                        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
                        ctx.lineTo(x + r, y + h);
                        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
                        ctx.lineTo(x, y + r);
                        ctx.quadraticCurveTo(x, y, x + r, y);
                        ctx.closePath();
                        ctx.fill();
                        ctx.stroke();
                        
                        ctx.shadowBlur = 0;
                        ctx.shadowOffsetX = 0;
                        ctx.shadowOffsetY = 0;
                        
                        ctx.fillStyle = '#4ec9b0';
                        ctx.font = "bold 20px 'Segoe UI', Arial, sans-serif";
                        ctx.textAlign = 'left';
                        ctx.textBaseline = 'top';
                        ctx.fillText("OptiSight CoT", x + 24, y + 24);
                        
                        const cotState = document.getElementById('cot-state');
                        const stateText = cotState ? cotState.textContent.trim() : 'RUNNING';
                        const badgeColor = stateText === 'RUNNING' ? '#007acc' : '#555';
                        
                        ctx.font = "bold 11px 'Segoe UI', Arial, sans-serif";
                        const stateTextWidth = ctx.measureText(stateText).width;
                        const badgeW = stateTextWidth + 20;
                        const badgeH = 24;
                        const badgeX = x + w - 24 - badgeW;
                        const badgeY = y + 22;
                        const br = 12;
                        
                        ctx.fillStyle = badgeColor;
                        ctx.beginPath();
                        ctx.moveTo(badgeX + br, badgeY);
                        ctx.lineTo(badgeX + badgeW - br, badgeY);
                        ctx.quadraticCurveTo(badgeX + badgeW, badgeY, badgeX + badgeW, badgeY + br);
                        ctx.quadraticCurveTo(badgeX + badgeW, badgeY + badgeH, badgeX + badgeW - br, badgeY + badgeH);
                        ctx.lineTo(badgeX + br, badgeY + badgeH);
                        ctx.quadraticCurveTo(badgeX, badgeY + badgeH, badgeX, badgeY + badgeH - br);
                        ctx.quadraticCurveTo(badgeX, badgeY, badgeX + br, badgeY);
                        ctx.closePath();
                        ctx.fill();
                        
                        ctx.fillStyle = 'white';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(stateText, badgeX + badgeW / 2, badgeY + badgeH / 2);
                        
                        ctx.strokeStyle = '#333';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(x + 24, y + 56);
                        ctx.lineTo(x + w - 24, y + 56);
                        ctx.stroke();
                        
                        ctx.fillStyle = '#dcdcaa';
                        ctx.font = "14px Consolas, Monaco, monospace";
                        ctx.textAlign = 'left';
                        ctx.textBaseline = 'top';
                        
                        let currentY = y + 68;
                        lines.forEach(line => {
                            ctx.fillText(line, x + 24, currentY);
                            currentY += lineHeight;
                        });
                    }

                    // 7. Upload
                    actionBtn.innerHTML = "Uploading...";
                    const dataURL = canvas.toDataURL('image/jpeg', 0.9);
                    const res = await fetch('/save_screenshot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: dataURL, prefix: 'Autonomous_Screenshot' })
                    });
                    const data = await res.json();
                    
                    if (data.status === 'success') {
                        if (typeof logDebug === 'function') {
                            logDebug(`<span style="color:#4ec9b0; font-weight:bold;">[Snapshot-FS] SUCCESS: Saved as ${data.filename}</span>`);
                        }
                        actionBtn.innerHTML = "Saved!";
                    } else {
                        throw new Error(data.message || "Unknown backend error");
                    }
                    
                    setTimeout(() => resetBtn(actionBtn, originalText), 2000);

                } catch (e) {
                    console.error("Screenshot error:", e);
                    if (typeof logDebug === 'function') logDebug(`<span style="color:#f44747">[Snapshot-FS] ERROR: ${e.message}</span>`);
                    alert("Screenshot failed: " + e.message);
                    resetBtn(actionBtn, originalText);
                }
            }
        