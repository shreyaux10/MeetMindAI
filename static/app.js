
// =====================================
// MEETMIND AI - JAVASCRIPT
// =====================================

const $ = (id) => document.getElementById(id);

// Main sections
const dashboardSection = $("dashboardSection");
const meetingSection = $("meetingSection");
const historySection = $("historySection");

// =====================================
// NAVIGATION
// =====================================

function showSection(section) {

    dashboardSection.classList.add("hidden");
    meetingSection.classList.add("hidden");
    historySection.classList.add("hidden");

    section.classList.remove("hidden");

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.remove("active");
    });
}

function showDashboard() {
    showSection(dashboardSection);
    $("dashboardBtn").classList.add("active");
}

function showMeeting() {
    showSection(meetingSection);
    $("newMeetingBtn").classList.add("active");
}

function showHistory() {
    showSection(historySection);
    $("historyBtn").classList.add("active");
    loadHistory();
}

// Navigation buttons
$("dashboardBtn").addEventListener("click", showDashboard);
$("newMeetingBtn").addEventListener("click", showMeeting);
$("historyBtn").addEventListener("click", showHistory);

$("startMeetingBtn").addEventListener("click", showMeeting);
$("createMeetingCard").addEventListener("click", showMeeting);


// =====================================
// API HELPER
// =====================================

async function api(url, options = {}) {

    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}


// =====================================
// CHECK BACKEND CONNECTION
// =====================================

async function checkBackend() {

    try {

        const data = await api("/api/health");

        $("aiStatus").textContent =
            data.ai_configured ? "Connected" : "API Key Missing";

        $("aiStatus").style.color =
            data.ai_configured ? "#159c70" : "#d14343";

    } catch (error) {

        $("aiStatus").textContent = "Offline";
        $("aiStatus").style.color = "#d14343";

    }
}


// =====================================
// DASHBOARD STATISTICS
// =====================================

async function updateStats() {

    try {

        const meetings = await api("/api/meetings");

        $("totalMeetings").textContent = meetings.length;

        let taskCount = 0;

        meetings.forEach(meeting => {
            taskCount += (meeting.action_items || []).length;
        });

        $("totalTasks").textContent = taskCount;

    } catch (error) {

        console.log("Statistics will be available after backend setup.");

    }
}


// =====================================
// AUDIO-TO-TEXT TRANSCRIPTION
// =====================================

$("audioFile").addEventListener("change", async function () {

    const audioFile = this.files[0];

    if (!audioFile) return;

    $("generateStatus").textContent =
        "Transcribing audio... Please wait.";

    $("generateStatus").style.color = "#7054df";

    const formData = new FormData();
    formData.append("audio", audioFile);

    this.disabled = true;

    try {

        const result = await api("/api/transcribe", {
            method: "POST",
            body: formData
        });

        $("transcript").value = result.transcript;

        $("generateStatus").textContent =
            "Audio transcribed successfully! You can now generate your AI summary.";

        $("generateStatus").style.color = "green";

    } catch (error) {

        $("generateStatus").textContent = error.message;
        $("generateStatus").style.color = "red";

    } finally {

        this.disabled = false;
        this.value = "";

    }

});

// =====================================
// GENERATE AI MEETING SUMMARY
// =====================================

$("generateBtn").addEventListener("click", async function () {

    const title = $("meetingTitle").value.trim();

    const attendees = $("attendees").value.trim();

    const transcript = $("transcript").value.trim();

    if (!transcript) {

        $("generateStatus").textContent =
            "Please enter meeting notes or a transcript first.";

        $("generateStatus").style.color = "red";

        return;
    }

    $("generateBtn").disabled = true;

    $("generateBtn").textContent = "AI is analyzing...";

    $("generateStatus").textContent =
        "Generating your meeting summary. Please wait...";

    $("generateStatus").style.color = "#7054df";

    try {

        const meeting = await api("/api/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                title: title || "Untitled Meeting",

                attendees: attendees,

                transcript: transcript

            })

        });

        displayResults(meeting);

        $("generateStatus").textContent =
            "Meeting summary generated and saved successfully!";

        $("generateStatus").style.color = "green";

        await updateStats();

    } catch (error) {

        $("generateStatus").textContent = error.message;

        $("generateStatus").style.color = "red";

    } finally {

        $("generateBtn").disabled = false;

        $("generateBtn").textContent = "✦ Generate AI Summary";

    }

});


// =====================================
// DISPLAY AI RESULTS
// =====================================

function displayResults(meeting) {

    $("resultSection").classList.remove("hidden");

    $("summaryText").textContent =
        meeting.summary || "No summary available.";

    fillList("keyPoints", meeting.key_points || []);

    fillList("decisions", meeting.decisions || []);

    displayTasks(meeting.action_items || []);

    $("resultSection").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}


// =====================================
// DISPLAY LISTS
// =====================================

function fillList(elementId, items) {

    const list = $(elementId);

    list.innerHTML = "";

    if (items.length === 0) {

        const item = document.createElement("li");

        item.textContent = "No information identified.";

        list.appendChild(item);

        return;
    }

    items.forEach(value => {

        const item = document.createElement("li");

        item.textContent =
            typeof value === "string" ? value : JSON.stringify(value);

        list.appendChild(item);

    });

}


// =====================================
// DISPLAY ACTION ITEMS
// =====================================

function displayTasks(tasks) {

    const container = $("actionItems");

    container.innerHTML = "";

    if (tasks.length === 0) {

        container.textContent = "No action items identified.";

        return;
    }

    tasks.forEach(task => {

        const row = document.createElement("div");

        row.className = "task-row";

        const title = document.createElement("strong");

        title.textContent = "☐ " + (task.task || "Task");

        const details = document.createElement("span");

        details.textContent =
            "Assignee: " + (task.assignee || "Not specified") +
            " | Deadline: " + (task.deadline || "Not specified") +
            " | Status: " + (task.status || "Pending");

        row.appendChild(title);

        row.appendChild(details);

        container.appendChild(row);

    });

}



// =====================================
// MEETING HISTORY
// =====================================


async function loadHistory() {

    const container = $("historyList");

    container.innerHTML = "<p>Loading meetings...</p>";

    try {

        const meetings = await api("/api/meetings");

        container.innerHTML = "";

        // GET FILTER VALUES
        const searchTerm = $("meetingSearch").value
            .trim()
            .toLowerCase();

        const startDate = $("startDate").value;
        const endDate = $("endDate").value;

        // FILTER MEETINGS
        const filteredMeetings = meetings.filter(meeting => {

            const title = (meeting.title || "").toLowerCase();
            const transcript = (meeting.transcript || "").toLowerCase();

            const matchesSearch =
                !searchTerm ||
                title.includes(searchTerm) ||
                transcript.includes(searchTerm);

            const meetingDate = (meeting.created_at || "").substring(0, 10);

            const matchesStartDate =
                !startDate || meetingDate >= startDate;

            const matchesEndDate =
                !endDate || meetingDate <= endDate;

            return matchesSearch &&
                   matchesStartDate &&
                   matchesEndDate;

        });

        if (filteredMeetings.length === 0) {

            container.textContent = meetings.length === 0
                ? "No meetings saved yet. Create your first meeting!"
                : "No meetings match your search or date filters.";

            return;
        }

        filteredMeetings.forEach(meeting => {

            const card = document.createElement("div");

            card.className = "history-card";

            const heading = document.createElement("h3");

            heading.textContent = meeting.title;

            const details = document.createElement("p");

            details.textContent =
                meeting.created_at + " | " +
                (meeting.action_items || []).length +
                " action items";

            // DELETE BUTTON
            const deleteBtn = document.createElement("button");

            deleteBtn.textContent = "Delete Meeting";

            deleteBtn.className = "delete-meeting-btn";

            deleteBtn.type = "button";

            deleteBtn.addEventListener("click", async (event) => {

                event.stopPropagation();

                const confirmed = confirm(
                    "Are you sure you want to delete this meeting?"
                );

                if (!confirmed) return;

                deleteBtn.disabled = true;

                deleteBtn.textContent = "Deleting...";

                try {

                    await api("/api/meetings/" + meeting.id, {
                        method: "DELETE"
                    });

                    alert("Meeting deleted successfully!");

                    await loadHistory();

                    await updateStats();

                } catch (error) {

                    alert(error.message);

                    deleteBtn.disabled = false;

                    deleteBtn.textContent = "Delete Meeting";

                }

            });

            card.appendChild(heading);

            card.appendChild(details);

            card.appendChild(deleteBtn);

            // OPEN MEETING DETAILS
            card.addEventListener("click", async () => {

                try {

                    const fullMeeting =
                        await api("/api/meetings/" + meeting.id);

                    showMeeting();

                    $("meetingTitle").value =
                        fullMeeting.title || "";

                    $("attendees").value =
                        fullMeeting.attendees || "";

                    $("transcript").value =
                        fullMeeting.transcript || "";

                    displayResults(fullMeeting);

                } catch (error) {

                    alert(error.message);

                }

            });

            container.appendChild(card);

        });

    } catch (error) {

        container.textContent = error.message;

    }

}

 // MEETING SEARCH AND DATE FILTERS

$("meetingSearch").addEventListener("input", loadHistory);

$("startDate").addEventListener("change", loadHistory);

$("endDate").addEventListener("change", loadHistory);

$("clearFiltersBtn").addEventListener("click", function () {

    $("meetingSearch").value = "";
    $("startDate").value = "";
    $("endDate").value = "";

    loadHistory();

});
  


 // =====================================
 // DOWNLOAD MEETING REPORT AS PDF
 // =====================================

 $("downloadPdfBtn").addEventListener("click", function () {

     if (!window.jspdf) {
         alert("PDF library is not loaded. Please refresh the page.");
         return;
     }

     const { jsPDF } = window.jspdf;
     const doc = new jsPDF();

     const pageWidth = doc.internal.pageSize.getWidth();
     const pageHeight = doc.internal.pageSize.getHeight();
     const margin = 18;
     const contentWidth = pageWidth - 2 * margin;

     let y = 20;

     function checkPageSpace(height = 12) {
         if (y + height > pageHeight - 18) {
             doc.addPage();
             y = 20;
         }
     }

     function addText(text, fontSize = 11, bold = false) {
         doc.setFont("helvetica", bold ? "bold" : "normal");
         doc.setFontSize(fontSize);
         doc.setTextColor(45, 45, 55);

         const lines = doc.splitTextToSize(
             String(text || "Not specified"),
             contentWidth
         );

         const lineHeight = fontSize * 0.48;

         lines.forEach(line => {
             checkPageSpace(lineHeight);
             doc.text(line, margin, y);
             y += lineHeight;
         });

         y += 4;
     }

     function addHeading(text) {
         checkPageSpace(16);
         y += 5;

         doc.setFont("helvetica", "bold");
         doc.setFontSize(14);
         doc.setTextColor(105, 75, 205);
         doc.text(text, margin, y);

         y += 9;
     }

     function addList(elementId) {
         const items = document.querySelectorAll(
             "#" + elementId + " li"
         );

         if (items.length === 0) {
             addText("No information identified.");
             return;
         }

         items.forEach((item, index) => {
             addText((index + 1) + ". " + item.textContent);
         });
     }

     // REPORT HEADER
     doc.setFillColor(105, 75, 205);
     doc.rect(0, 0, pageWidth, 35, "F");

     doc.setFont("helvetica", "bold");
     doc.setFontSize(21);
     doc.setTextColor(255, 255, 255);
     doc.text("MeetMind AI", margin, 17);

     doc.setFontSize(10);
     doc.text("AI Meeting Intelligence Report", margin, 25);

     y = 47;

     // MEETING INFORMATION
     addText($("meetingTitle").value || "Untitled Meeting", 17, true);

     addText("Attendees: " + (
         $("attendees").value || "Not specified"
     ));

     addText("Report generated: " + new Date().toLocaleString());

     // SUMMARY
     addHeading("Meeting Summary");
     addText($("summaryText").textContent);

     // KEY POINTS
     addHeading("Key Discussion Points");
     addList("keyPoints");

     // DECISIONS
     addHeading("Decisions Made");
     addList("decisions");

     // ACTION ITEMS
     addHeading("Action Items");

     const tasks = document.querySelectorAll(
         "#actionItems .task-row"
     );

     if (tasks.length === 0) {
         addText("No action items identified.");
     } else {
         tasks.forEach((task, index) => {
             addText(
                 (index + 1) + ". " +
                 task.textContent.trim().replace(/\s+/g, " ")
             );
         });
     }

     // PAGE NUMBERS
     const totalPages = doc.getNumberOfPages();

     for (let page = 1; page <= totalPages; page++) {
         doc.setPage(page);
         doc.setFontSize(9);
         doc.setTextColor(130, 130, 130);
         doc.text(
             "MeetMind AI | Page " + page + " of " + totalPages,
             margin,
             pageHeight - 10
         );
     }

     const filename = (
         $("meetingTitle").value || "Meeting_Report"
     )
         .replace(/[^a-z0-9_-]/gi, "_")
         .slice(0, 60);

     doc.save(filename + ".pdf");

 });

// =====================================
// INITIALIZE APPLICATION
// =====================================

showDashboard();

checkBackend();

updateStats();
