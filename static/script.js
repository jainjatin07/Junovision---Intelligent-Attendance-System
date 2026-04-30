// Smooth scroll to upload section
function scrollToUpload() {
    document.getElementById('upload').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// ---------- IMAGE UPLOAD & PREVIEW ----------
const fileInput = document.getElementById('fileInput');
const markBtn = document.getElementById('markAttendanceBtn');
const previewImage = document.getElementById('previewImage');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const imagePreview = document.getElementById('imagePreview');

if (fileInput) {
    fileInput.addEventListener("change", function (e) {
        const file = e.target.files[0];
        if (file) handleFileSelect(file);
    });
}

imagePreview.addEventListener('dragover', (e) => {
    e.preventDefault();
    imagePreview.classList.add("drag-over");
});

imagePreview.addEventListener('dragleave', () => {
    imagePreview.classList.remove("drag-over");
});

imagePreview.addEventListener('drop', (e) => {
    e.preventDefault();
    imagePreview.classList.remove("drag-over");

    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
        handleFileSelect(file);
    }
});

imagePreview.addEventListener("click", () => {
    fileInput.click();
});

function handleFileSelect(file) {
    const reader = new FileReader();
    reader.onload = function (event) {
        previewImage.src = event.target.result;
        previewImage.style.display = "block";
        uploadPlaceholder.style.display = "none";

        markBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

// ---------- MARK ATTENDANCE (CONNECTS TO BACKEND) ----------
function markAttendance() {
    const overlay = document.getElementById("processingOverlay");
    const progressFill = document.getElementById("progressFill");
    const progressPercentage = document.getElementById("progressPercentage");

    overlay.classList.add("active");

    let prog = 0;
    let animation = setInterval(() => {
        prog += 2;
        progressFill.style.width = prog + "%";
        progressPercentage.textContent = prog + "%";

        if (prog >= 100) clearInterval(animation);
    }, 40);

    let formData = new FormData();
    formData.append("image", fileInput.files[0]);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            overlay.classList.remove("active");
            showResults(data.students, data.csv_file);
        })
        .catch(err => {
            overlay.classList.remove("active");
            alert("Error processing image!");
            console.error(err);
        });
}

// ---------- SHOW ATTENDANCE RESULTS ----------
function showResults(students, csvFile) {
    const resultSection = document.getElementById("result");
    const studentsList = document.getElementById("studentsList");
    const resultCount = document.getElementById("resultCount");

    resultSection.style.display = "block";
    studentsList.innerHTML = "";
    resultCount.textContent = `${students.length} students detected`;

    window.generatedCSV = csvFile;

    students.forEach((name, i) => {
        let item = document.createElement("div");
        item.className = "student-item";
        item.style.animationDelay = `${i * 0.1}s`;

        item.innerHTML = `
            <div class="student-avatar">
                <div class="result-avatar">${name.charAt(0)}</div>
            </div>

            <div class="student-info">
                <h3>${name}</h3>
                <p>ID: AUTO</p>
            </div>

            <div class="student-status">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                     fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11V12A10 10 0 1 1 16 2"/>
                    <polyline points="22 4 12 14 9 11"/>
                </svg>
                <span>Present</span>
            </div>
        `;

        studentsList.appendChild(item);
    });

    resultSection.scrollIntoView({ behavior: "smooth" });
}

// ---------- DOWNLOAD GENERATED CSV ----------
function downloadCSV() {
    if (!window.generatedCSV) {
        alert("CSV not generated yet!");
        return;
    }

    window.location.href = `/download/${window.generatedCSV}`;
}

// ---------- RESET ----------
function resetUpload() {
    document.getElementById("result").style.display = "none";

    previewImage.style.display = "none";
    uploadPlaceholder.style.display = "flex";
    previewImage.src = "";

    fileInput.value = "";
    markBtn.disabled = true;

    document.getElementById("upload").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}
