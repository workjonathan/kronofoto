const toggleVis = evt => {
    //console.writeline('something has happened')
    const el = document.querySelector('#metadata')
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
    }
}
