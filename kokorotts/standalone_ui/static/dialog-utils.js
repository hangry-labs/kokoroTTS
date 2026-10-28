export function closeDialogOnBackdrop(dialog, close) {
  dialog.addEventListener('pointerdown', (event) => {
    if (event.button !== 0 || event.target !== dialog) return
    const bounds = dialog.getBoundingClientRect()
    const outside = event.clientX < bounds.left
      || event.clientX > bounds.right
      || event.clientY < bounds.top
      || event.clientY > bounds.bottom
    if (outside) close()
  })
}
