const toast = document.querySelector('.toast')
let toastTimer

function showToast(message) {
  window.clearTimeout(toastTimer)
  toast.textContent = message
  toast.hidden = false
  toastTimer = window.setTimeout(() => { toast.hidden = true }, 1800)
}

document.querySelectorAll('[data-copy-target]').forEach((button) => {
  button.addEventListener('click', async () => {
    const source = document.getElementById(button.dataset.copyTarget)
    try {
      await navigator.clipboard.writeText(source.textContent)
      showToast('Copied to clipboard')
    } catch {
      showToast('Clipboard access was unavailable')
    }
  })
})
