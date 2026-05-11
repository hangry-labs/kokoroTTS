const canvas = document.getElementById("shapes");
const ctx = canvas.getContext("2d");
const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const fontSize = 16;
const frameInterval = 100;

let columns = 0;
let drops = [];
let lastUpdate = 0;

function resetCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  columns = Math.floor(canvas.width / fontSize);
  drops = [];

  for (let i = 0; i < columns; i++) {
    drops[i] = [
      Math.random() * -100,
      Math.random() * -200,
    ];
  }
}

function draw(timestamp) {
  if (timestamp - lastUpdate < frameInterval) {
    requestAnimationFrame(draw);
    return;
  }
  lastUpdate = timestamp;

  ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.font = `${fontSize}px monospace`;

  for (let i = 0; i < drops.length; i++) {
    for (let j = 0; j < drops[i].length; j++) {
      const text = letters.charAt(Math.floor(Math.random() * letters.length));
      ctx.fillStyle = "#ff6b00";
      ctx.fillText(text, i * fontSize, drops[i][j] * fontSize);

      if (drops[i][j] * fontSize > canvas.height && Math.random() > 0.975) {
        drops[i][j] = 0;
      }

      drops[i][j]++;
    }
  }

  requestAnimationFrame(draw);
}

window.addEventListener("resize", resetCanvas);
resetCanvas();
requestAnimationFrame(draw);
