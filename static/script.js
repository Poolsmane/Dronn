const form = document.getElementById('scrape-form');
const spinner = document.getElementById('loading-spinner');
const message = document.getElementById('message');
const tableBody = document.querySelector("#results-table tbody");
const paginationControls = document.getElementById('pagination-controls');
const rowsPerPageSelect = document.getElementById('rowsPerPage');
const globalSearchInput = document.getElementById('globalSearch');

let filters = {
    bidNumber: null,
    items: null,
    quantityCondition: null,
    department: null,
    startDate: null,
    endDate: null
};
let data = [];
let currentPage = 1;
let rowsPerPage = parseInt(rowsPerPageSelect.value);

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    spinner.style.display = 'inline-block';
    message.classList.add('d-none');
    tableBody.innerHTML = '';
    paginationControls.innerHTML = '';

    const keyword = document.getElementById('keyword').value;
    const formData = new FormData();
    formData.append('keyword', keyword);

    try {
        const scrapeRes = await fetch('/scrape', {
            method: 'POST',
            body: formData
        });

        const scrapeText = await scrapeRes.text();

        if (!scrapeRes.ok) {
            throw new Error(scrapeText || 'Scraping failed');
        }

        const dataRes = await fetch('/data');
        const dataJson = await dataRes.json();

        if (dataJson.error) {
            throw new Error(dataJson.error);
        }

        data = dataJson.data;
        applyFilters();
        createPagination();
        showPage(currentPage);

        message.className = "alert alert-success mt-3";
        message.textContent = "Scraping and results loaded successfully!";
        message.classList.remove('d-none');
    } catch (err) {
        message.className = "alert alert-danger mt-3";
        message.textContent = `Error: ${err.message}`;
        message.classList.remove('d-none');
    } finally {
        spinner.style.display = 'none';
    }
});

function applyFilters() {
    const globalSearch = globalSearchInput.value.trim().toLowerCase();

    const filteredData = data.filter(row => {
        if (globalSearch) {
            const rowValues = Object.values(row).join(" ").toLowerCase();
            if (!rowValues.includes(globalSearch)) return false;
        }

        if (filters.bidNumber && !row["Bid Number"].toString().toLowerCase().includes(filters.bidNumber.toLowerCase())) return false;
        if (filters.items && !row["Items"].toString().toLowerCase().includes(filters.items.toLowerCase())) return false;

        if (filters.quantityCondition) {
            const quantity = row["Quantity"];
            const [operator, value] = filters.quantityCondition.split(/([<>]=?)/).filter(Boolean);
            const numericValue = parseInt(value);
            if (operator === '>' && quantity <= numericValue) return false;
            if (operator === '<' && quantity >= numericValue) return false;
            if (operator === '=' && quantity !== numericValue) return false;
        }

        if (filters.department && !row["Department"].toString().toLowerCase().includes(filters.department.toLowerCase())) return false;
        if (filters.startDate && new Date(row["Start Date"]) < new Date(filters.startDate)) return false;
        if (filters.endDate && new Date(row["End Date"]) > new Date(filters.endDate)) return false;

        return true;
    });

    return filteredData;
}

function createPagination() {
    const totalPages = Math.ceil(data.length / rowsPerPage);
    paginationControls.innerHTML = '';
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.classList.add('page-item');
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', () => showPage(i));
        paginationControls.appendChild(li);
    }
}

function showPage(page) {
    currentPage = page;
    const filteredData = applyFilters();
    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const pageData = filteredData.slice(start, end);
    tableBody.innerHTML = '';

    pageData.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row["Bid Number"]}</td>
            <td>${row["Items"]}</td>
            <td>${row["Quantity"]}</td>
            <td>${row["Department"]}</td>
            <td>${row["Start Date"]}</td>
            <td>${row["End Date"]}</td>
            <td><a href="${row["Downloadable File URL"]}" target="_blank" class="btn btn-sm btn-outline-primary download-link">Download</a></td>
        `;
        tableBody.appendChild(tr);
    });

    // Attach event listeners to download links
    document.querySelectorAll('.download-link').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            console.log("Download link clicked");

            // Simulate file processing or any other task before showing the popup
            setTimeout(function() {
                openAiPopup();  // Open the popup after a 5-second delay

                // After opening the popup, navigate to the download link
                window.open(event.target.href, '_blank');  // Open the download link in a new tab
            }, 5000); // 5000 milliseconds = 5 seconds
        });
    });
}

document.getElementById('quantity-filter').addEventListener('input', (e) => {
    filters.quantityCondition = e.target.value;
    showPage(currentPage);
});

document.querySelectorAll('#results-table thead input').forEach(input => {
    input.addEventListener('input', () => {
        const column = input.getAttribute('data-col');
        const value = input.value;
        filters[column] = value;
        showPage(currentPage);
    });
});

document.getElementById('start-date').addEventListener('change', (e) => {
    filters.startDate = e.target.value;
    showPage(currentPage);
});

document.getElementById('end-date').addEventListener('change', (e) => {
    filters.endDate = e.target.value;
    showPage(currentPage);
});

rowsPerPageSelect.addEventListener('change', (e) => {
    rowsPerPage = parseInt(e.target.value);
    showPage(currentPage);
    createPagination();
});

globalSearchInput.addEventListener('input', () => {
    currentPage = 1;
    createPagination();
    showPage(currentPage);
});

// Function to open the AI popup after a delay
function openAiPopup() {
    const aiPopup = document.getElementById("ai-agent-popup");
    const statusMessage = document.getElementById("status-message");
    const queryFormPopup = document.getElementById("query-form-popup");

    // Ensure the popup is displayed
    aiPopup.style.display = "block"; // Popup is visible

    // Update status message and show the question form
    statusMessage.innerText = "File has been processed. You can now ask questions.";
    queryFormPopup.style.display = "block";  // Show the question form
}

// Handle question submission
document.getElementById("query-form-popup").addEventListener("submit", function(event) {
    event.preventDefault();
    
    const question = document.getElementById("question_popup").value;

    // Send the question to the backend for processing
    fetch('/ask_question', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: question })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("popup-answer").innerText = "Answer: " + data.answer;
        } else {
            document.getElementById("popup-answer").innerText = "Error: " + data.error;
        }
    })
    .catch(error => {
        document.getElementById("popup-answer").innerText = "Error occurred: " + error.message;
    });
});

// Close the popup
document.getElementById("close-ai-popup").addEventListener("click", function() {
    document.getElementById("ai-agent-popup").style.display = "none";
});
