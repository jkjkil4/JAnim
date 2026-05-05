document.addEventListener('DOMContentLoaded', () => {
    const current = document.querySelector('div.sidebar-tree a.current');
    if (!current) return;

    // Find the nearest scrollable ancestor (the sidebar container)
    const getScrollParent = (node) => {
        let p = node.parentElement;
        const html = document.documentElement;
        while (p && p !== html) {
            const cs = getComputedStyle(p);
            const oy = cs.overflowY;
            if ((oy === 'auto' || oy === 'scroll') && p.scrollHeight > p.clientHeight) {
                return p;
            }
            p = p.parentElement;
        }
        return null;
    };

    const container = getScrollParent(current) || document.querySelector('div.sidebar-tree');
    if (!container) return;

    // Compute current's top relative to the container
    let offset = current.offsetTop;
    let node = current.offsetParent;
    while (node && node !== container) {
        offset += node.offsetTop;
        node = node.offsetParent;
    }

    // Center the current item within the sidebar container without affecting body scroll
    const targetTop = offset - (container.clientHeight - current.clientHeight) / 2;
    container.scrollTo({ top: Math.max(0, targetTop), behavior: 'auto' });
});