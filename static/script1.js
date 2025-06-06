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

const askButton = document.getElementById("askButton");

function readTextFile() {
    fetch('../status.txt')
      .then(response => {
        if (!response.ok) {
          throw new Error('File not found or inaccessible');
        }
        return response.text();
      })
      .then(text => {
        // debugger
        // console.log(text)
        document.getElementById("agenttext").textContent = text === "done"? "":  "File is still processing..";
        askButton.disabled = text === "done"? false : true;
      })
      .catch(error => {
        console.log(error)
      });
  }

  // Call initially and then every 2 seconds
  readTextFile();
  setInterval(readTextFile, 2000);
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const keyword = document.getElementById('keyword').value.trim();
    if (!keyword) {
        message.className = "alert alert-warning mt-3";
        message.textContent = "Please enter a keyword to scrape.";
        message.classList.remove('d-none');
        return;
    }

    spinner.style.display = 'inline-block';
    message.classList.add('d-none');
    tableBody.innerHTML = '';
    paginationControls.innerHTML = '';

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

        await new Promise(resolve => setTimeout(resolve, 1500)); // Wait for backend to process

        const dataRes = await fetch('/data');
        const dataJson = await dataRes.json();

        if (dataJson.error) {
            throw new Error(dataJson.error);
        }

        data = dataJson.data;
        currentPage = 1;

        // 🔁 This was previously in window.onload – move it here
        filteredData = data;
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



window.onload = function () {
    spinner.style.display = 'none';
    tableBody.innerHTML = '';
    paginationControls.innerHTML = '';
    message.classList.add('d-none');
    askButton.disabled = true;
    const isDisabled = localStorage.getItem("askButtonDisabled") === "true";
    askButton.disabled = isDisabled;
};



// Automatically run scraping for keywords on page load
// window.onload = async function () {
//     // const keywords = ['Semi Conductor','Hiring for IT Professionals','Learning Management system','Software development','Hiring for IT Manpower','Mobile application'];
//     // const keywords = ['Mobile application'];

//     spinner.style.display = 'inline-block';
//     tableBody.innerHTML = '';
//     paginationControls.innerHTML = '';
//     message.classList.add('d-none');
//     let allResults = [];

//     // for (const keyword of keywords) {
//     //     const formData = new FormData();
//     //     formData.append('keyword', keyword);

//     //     try {
//     //         const scrapeRes = await fetch('/scrape', {
//     //             method: 'POST',
//     //             body: formData
//     //         });

//     //         const scrapeText = await scrapeRes.text();

//     //         if (!scrapeRes.ok) {
//     //             console.error(`Scrape failed for ${keyword}:`, scrapeText);
//     //             continue;
//     //         }

//     //         await new Promise(resolve => setTimeout(resolve, 3000)); // 3 seconds       
            

//     //         // if (dataJson.error) {
//     //         //     console.error(`Data error for ${keyword}:`, dataJson.error);
//     //         //     continue;
//     //         // }

//     //         // allResults = allResults.concat(dataJson.data);
//     //     } catch (err) {
//     //         console.error(`Error during scraping for ${keyword}:`, err);
//     //     }
//     // }
//     const dataRes = await fetch('/data');
//     const dataJson = await dataRes.json();
//     data = dataJson.data;
//     filteredData = data;
//     createPagination();
//     showPage(currentPage);

//     message.className = "alert alert-success mt-3";
//     message.textContent = "Automatic scraping and results loaded successfully!";
//     message.classList.remove('d-none');
//     spinner.style.display = 'none';
// };

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

// Helper to parse "DD-MM-YYYY hh:mm AM/PM" into a Date object
function parseCustomDate(dateString) {
    // Example input: "22-04-2025 12:31 PM"
    const [datePart, timePart, meridian] = dateString.split(" ");
    const [day, month, year] = datePart.split("-").map(Number);
    let [hour, minute] = timePart.split(":").map(Number);

    // Convert 12-hour time to 24-hour time
    if (meridian === "PM" && hour !== 12) hour += 12;
    if (meridian === "AM" && hour === 12) hour = 0;

    return new Date(year, month - 1, day, hour, minute);
}

function applyFilters() {
    const globalSearch = globalSearchInput.value.trim().toLowerCase();

    const filteredData = data.filter(row => {
        if (globalSearch) {
            const rowValues = Object.values(row).join(" ").toLowerCase();
            if (!rowValues.includes(globalSearch)) return false;
        }

        if (filters.bidNumber && !row["Bid Number"].toString().toLowerCase().includes(filters.bidNumber.toLowerCase())) return false;

        if (filters.items) {
            const itemKeywords = filters.items.toLowerCase().split(/\s+/);
            const itemContent = row["Items"].toString().toLowerCase();
            const matchesItem = itemKeywords.some(keyword => itemContent.includes(keyword));
            if (!matchesItem) return false;
        }

        if (filters.quantityCondition) {
            const quantity = row["Quantity"];
            const [operator, value] = filters.quantityCondition.split(/([<>]=?)/).filter(Boolean);
            const numericValue = parseInt(value);
            if (operator === '>' && quantity <= numericValue) return false;
            if (operator === '<' && quantity >= numericValue) return false;
            if (operator === '=' && quantity !== numericValue) return false;
        }

        if (filters.department && !row["Department"].toString().toLowerCase().includes(filters.department.toLowerCase())) return false;

        const rowStartDate = parseCustomDate(row["Start Date"]);
        const rowEndDate = parseCustomDate(row["End Date"]);

        if (filters.startDate && !filters.endDate) {
            const filterStart = new Date(filters.startDate);
            if (rowStartDate < filterStart) return false;
        }

        if (!filters.startDate && filters.endDate) {
            const filterEnd = new Date(filters.endDate);
            if (rowEndDate > filterEnd) return false;
        }

        if (filters.startDate && filters.endDate) {
            const filterStart = new Date(filters.startDate);
            const filterEnd = new Date(filters.endDate);
            if (rowStartDate < filterStart || rowEndDate > filterEnd) return false;
        }

        return true;
    });

    return filteredData;
}

// Date input listeners
document.getElementById('start-date').addEventListener('change', (e) => {
    filters.startDate = e.target.value;
    showPage(currentPage);
});

document.getElementById('end-date').addEventListener('change', (e) => {
    filters.endDate = e.target.value;
    showPage(currentPage);
});


let curr = 1;
let currentWindowStart = 1;
const windowSize = 10;

function createPagination() {
    const totalPages = Math.ceil(data.length / rowsPerPage);
    paginationControls.innerHTML = '';

    const windowEnd = Math.min(currentWindowStart + windowSize - 1, totalPages);

    // Add Prev button if applicable
    if (totalPages > 20 && currentWindowStart > 1) {
        const prevLi = document.createElement('li');
        prevLi.classList.add('page-item');
        prevLi.innerHTML = `<a class="page-link" href="#">Prev</a>`;
        prevLi.addEventListener('click', () => {
            currentWindowStart = Math.max(currentWindowStart - windowSize, 1);
            createPagination();
        });
        paginationControls.appendChild(prevLi);
    }

    // Add page number buttons
    for (let i = currentWindowStart; i <= windowEnd; i++) {
        const li = document.createElement('li');
        li.classList.add('page-item');
        if (i === curr) li.classList.add('active');
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', () => {
            curr = i;
            showPage(i);
            createPagination();
        });
        paginationControls.appendChild(li);
    }

    // Add Next button if applicable
    if (totalPages > 20 && windowEnd < totalPages) {
        const nextLi = document.createElement('li');
        nextLi.classList.add('page-item');
        nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
        nextLi.addEventListener('click', () => {
            currentWindowStart = currentWindowStart + windowSize;
            createPagination();
        });
        paginationControls.appendChild(nextLi);
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
            <td><a href="${row["Downloadable File URL"]}" class="btn btn-sm btn-outline-primary download-link">Ask Agent</a></td>
        `;
        tableBody.appendChild(tr);
    });

    document.querySelectorAll('.download-link').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            console.log("Download link clicked");
    
            setTimeout(function() {
                openAiPopup();
                const a = document.createElement('a');
                a.href = event.target.href;
                a.setAttribute('download', ''); // This hints the browser to download
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }, 1500);
        });
    });
    
}

document.getElementById('quantity-filter').addEventListener('input', (e) => {
    filters.quantityCondition = e.target.value;
    showPage(currentPage);
});
document.getElementById('items-filter').addEventListener('input', (e) => {
    filters.items = e.target.value;
    showPage(currentPage);
});
document.getElementById('bids-filter').addEventListener('input', (e) => {
    filters.bidNumber = e.target.value;
    showPage(currentPage);
});document.getElementById('department-filter').addEventListener('input', (e) => {
    filters.department = e.target.value;
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
    applyFilters()
    showPage(currentPage);
});

function openAiPopup() {
    const aiPopup = document.getElementById("ai-agent-popup");
    const statusMessage = document.getElementById("status-message");
    const queryFormPopup = document.getElementById("query-form-popup");

    aiPopup.style.display = "block";
    statusMessage.innerText = "File has been processed. You can now ask questions.";
    queryFormPopup.style.display = "block";
}

document.getElementById("query-form-popup").addEventListener("submit", function(event) {
    event.preventDefault();

    const question = document.getElementById("question_popup").value;

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

document.getElementById("close-ai-popup").addEventListener("click", function() {
    document.getElementById("ai-agent-popup").style.display = "none";
});

function disableButton() {
    askButton.disabled = true;
    localStorage.setItem("askButtonDisabled", "true");
  }

  // Function to enable the button and save the state
  function enableButton() {
    askButton.disabled = false;
    localStorage.setItem("askButtonDisabled", "false");
  }