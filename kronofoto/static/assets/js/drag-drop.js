window.addEventListener('DOMContentLoaded', () => {
const marker = document.querySelector('.active-year-marker');
const dropzones = document.querySelectorAll('.tl a');
const dzXCoords = Array.from(dropzones).map((dropzone) => dropzone.getBoundingClientRect().x);

// console.log(marker);
// console.log(dropzones);
// console.log(dzXCoords);

const getClosestDropzoneX = (goal) => {
  return dzXCoords.reduce((prev, curr) => {
    return (Math.abs(curr - goal) < Math.abs(prev - goal) ? curr : prev);
  });
};

// console.log(getClosestDropzoneX(800));

// Marker Listeners
marker.addEventListener('dragstart', dragStart);
marker.addEventListener('dragend', dragEnd);
marker.addEventListener('drag', dragHandler);
marker.addEventListener('mousedown', mouseDown);
marker.addEventListener('mouseup', mouseUp);
marker.addEventListener('mousemove', mouseMove);
// Loop through dropzones and call drag events
Array.from(dropzones).map((dropzone) => {
  
  dropzone.addEventListener('dragover', dragOver);
  dropzone.addEventListener('dragenter', dragEnter);
  dropzone.addEventListener('dragleave', dragLeave);
  dropzone.addEventListener('drop', dragDrop);
  // console.log(dropzone);
});

let currentX;
let initialX;
let xOffset = 0;
let markerWidth = (marker.getBoundingClientRect().width / 2);
let currentTick;
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

// ==============================================
// Drag Functions
// ==============================================
function dragStart(e) {
  e.dataTransfer.setDragImage(dragImgEl, 0, 0);
  initialX = e.clientX; // where mouse was when drag start

  setTimeout(() => { this.className += ' no-point'; }, 0);
}

function dragHandler(e) {
  // console.log('dragHandler');
  let prevX;
  e.preventDefault();
  // currentX = e.clientX - initialX; // The difference between mouse start and current mouse
  currentX = e.clientX;
  xOffset = currentX;
  // console.log(`currentX: ${currentX}`);
  // console.log(e.clientX);
  if (currentX <= 0) {
    e.target.style.transform = `translateX(${initialX - markerWidth}px)`; // 145 - 100 - 5.5 - 5 = 34.5
  }
  else {
    e.target.style.transform = `translateX(${e.clientX - markerWidth}px)`; // 145 - 100 - 5.5 - 5 = 34.5
  }
  prevX = currentX;

}

function dragEnd(e) {
  e.preventDefault();
  // console.log(`DRAG:END -- currentX: ${currentX}`);
  // initialX = currentX;
  // console.log(this);
  this.classList.remove('no-point');
  let destination = getClosestDropzoneX(currentX);
  if (currentX <= 0) {
    e.target.style.transform = `translateX(${currentTickX}px)`;
  }
  else {
    e.target.style.transform = `translateX(${currentX - markerWidth}px)`;
  }
  // let parentUrl = currentTick.parentElement.getAttribute('xlink:href');
  // console.log(currentTick.parentElement.getAttribute('xlink:href'));
  // let parent = document.querySelectorAll(`[*|href="${parentUrl}"]`);
  // let $theLink = $(`svg a[*|href="${parentUrl}"]`);

  // window.location.href = parentUrl;
  const jsonhref = currentTick.getAttribute('data-json-href') || currentTick.parentElement.getAttribute('data-json-href');
  request('GET', jsonhref).then(data => {
    loadstate(data);
    window.history.pushState(data, 'Fortepan Iowa', data.url);
  });
}

function dragOver(e) {
  e.preventDefault();
  currentTick = e.target;
  currentTickX = currentTick.getBoundingClientRect().x;
  // console.log('dragOver');
}

function dragEnter(e) {
  e.preventDefault();
  // console.log('dragEnter');

}

function dragLeave(e) {
  e.preventDefault();
  // console.log('dragLeave');
}

function dragDrop(e) {
  e.preventDefault();
}
// ==============================================
});