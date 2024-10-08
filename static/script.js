feather.replace();
document.addEventListener("DOMContentLoaded", function () {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const send = document.getElementById("sendMessage");
  const clear = document.getElementById("clearMessage");

  function sendMessage() {
    const message = userInput.value.trim();
    if (message) {
      // Reset chat box
      chatBox.innerHTML = "";
      userInput.value = "";

      // Kirim pesan user ke server
      fetch("/gen_query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ userMessage: message }),
      })
        .then((response) => {
          // Jika respons dari server tidak OK, lemparkan error
          if (!response.ok) {
            throw new Error(
              "Server returned " + response.status + " : " + response.statusText
            );
          }
          // Cek apakah response type adalah JSON
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.indexOf("application/json") !== -1) {
            return response.json();
          } else {
            throw new Error("Server response is not in JSON format.");
          }
        })
        .then((data) => {
          // Menangani data dari server
          if (data.table_result) {
            addMessage("Terdapat " + data.table_result + " Container.", "bot");
          } else if (data.table_html && data.summary && data.csv_url) {
            // Add the HTML table to the chatbot
            addTable(data.table_html, "bot");
            // Add a download button for the table
            addDownloadButton(data.csv_url, "bot");
            addMessage(data.summary, "bot");
          } else {
            // Jika tidak ada table, tampilkan pesan error
            addMessage("Data tidak ditemukan.", "bot");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          addMessage("Sorry, something went wrong. " + error.message, "bot");
        });
    }
  }

  function addDownloadButton(csvUrl, type) {
    const buttonDiv = document.createElement("div");
    buttonDiv.classList.add("chat-message", type);

    const downloadButton = document.createElement("a");
    downloadButton.href = csvUrl; // Set the URL to the CSV download link
    downloadButton.innerHTML = "Download Table"; // Button text
    downloadButton.classList.add("download-button");
    downloadButton.download = "pivot_table.csv"; // Specify the download filename
    downloadButton.style.padding = "10px 20px 10px 10px";
    downloadButton.style.backgroundColor = "#28a745";
    downloadButton.style.color = "#fff";
    downloadButton.style.borderRadius = "1px 10px 10px 10px";
    downloadButton.style.textDecoration = "none";
    downloadButton.style.marginLeft = "20px";

    buttonDiv.appendChild(downloadButton);
    chatBox.appendChild(buttonDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function clearMessage() {
    const chatBox = document.getElementById("chat-box");
    chatBox.innerHTML = ""; // Mengosongkan seluruh konten di chat box
  }

  function addMessage(message, type) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("chat-message", type);
    messageDiv.innerHTML = `<div class="message">${message}</div>`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Fungsi untuk menampilkan tabel HTML di chat box
  function addTable(tableHTML, type) {
    const tableDiv = document.createElement("div");
    tableDiv.classList.add("chat-message", type);

    // Bungkus tabel dengan div yang memiliki overflow-x: auto
    const wrapperDiv = document.createElement("div");
    wrapperDiv.classList.add("table-wrapper");
    wrapperDiv.innerHTML = tableHTML;

    tableDiv.appendChild(wrapperDiv);
    chatBox.appendChild(tableDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Kirim pesan saat Enter ditekan
  userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  // Tambahkan event listener untuk tombol 'Send'
  send.addEventListener("click", sendMessage);

  // Tambahkan event listener untuk tombol 'Clear'
  clear.addEventListener("click", clearMessage);
});
