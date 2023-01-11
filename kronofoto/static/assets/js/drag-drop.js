// =======================================================================================================
// This file contains the functionality to enable the dragging and dropping of the timeline marker to work
// =======================================================================================================
let currentX
let currentTick
let root
window.addEventListener("dragover", e => {
    currentX = e.clientX
    let closestTick
    for (const el of root.querySelectorAll('.tl a')) {
      const rect = el.getBoundingClientRect()
      if (rect.left <= currentX && currentX <= rect.right) {
          closestTick = el
      }
    }
    currentTick = closestTick
})
export const enableMarkerDnD = document => {
    root = document
    const now = Date.now()
    const marker = document.querySelector('.active-year-marker');
    const dropzones = document.querySelectorAll('.tl a');
    const dzXCoords = Array.from(dropzones).map((dropzone) => dropzone.getBoundingClientRect().x);

    // This finds the closest tick to where the cursor is during the drag.
    const getClosestDropzoneX = (goal) => {
      return dzXCoords.reduce((prev, curr) => {
        return (Math.abs(curr - goal) < Math.abs(prev - goal) ? curr : prev);
      });
    };

    // Marker Listeners
    marker.addEventListener('dragstart', dragStart);
    marker.addEventListener('dragend', dragEnd);
    marker.addEventListener('drag', dragHandler);
    marker.addEventListener('mousedown', mouseDown);
    marker.addEventListener('mouseup', mouseUp);
    marker.addEventListener('mousemove', mouseMove);
    // Loop through dropzones and call drag events
    Array.from(dropzones).forEach((dropzone) => {
      
      dropzone.addEventListener('dragover', dragOver);
      dropzone.addEventListener('dragenter', dragEnter);
      dropzone.addEventListener('dragleave', dragLeave);
      dropzone.addEventListener('drop', dragDrop);
    });

    let initialX;
    let xOffset = 0;
    let markerWidth = (marker.getBoundingClientRect().width / 2);
    let currentTickX;

    // Make invisible drag feedback image
    const dragImgEl = document.createElement('span');
    dragImgEl.setAttribute('style', 'position: absolute; display: block; top: 0; left: 0; width: 0; height: 0;' );
    document.body.appendChild(dragImgEl);

    // ==============================================
    // Necessary to prevent mirror image from showing
    // ==============================================
    function mouseDown(e) {}

    function mouseUp(e) {}

    function mouseMove(e) {
      e.preventDefault();
    }

    // ==============================================
    // Drag Functions
    // ==============================================
    function dragStart(e) {
      e.dataTransfer.setDragImage(dragImgEl, 0, 0);
      initialX = e.clientX; // where mouse was when drag start

      setTimeout(() => { this.className += ' no-point'; }, 0);
    }

    function dragHandler(e) {
      let prevX;
      e.preventDefault();
      if (currentX <= 0) {
        e.target.style.transform = `translateX(${initialX - markerWidth}px)`;
      }
      else {
        e.target.style.transform = `translateX(${currentX - markerWidth}px)`;
      }
      prevX = currentX;
    }

    function dragEnd(e) {
      e.preventDefault();
      this.classList.remove('no-point');
      let destination = getClosestDropzoneX(currentX); // not used?
      if (currentX <= 0) {
        e.target.style.transform = `translateX(${currentTickX}px)`;
      }
      else {
        e.target.style.transform = `translateX(${currentX - markerWidth}px)`;
      }

      currentTick.dispatchEvent(new Event("click"))
    }

    function dragOver(e) {
      e.preventDefault();
      currentX = e.clientX;
      xOffset = currentX;
    }

    function dragEnter(e) {
      e.preventDefault();
    }

    function dragLeave(e) {
      e.preventDefault();
    }

    function dragDrop(e) {
      e.preventDefault();
    }
}
