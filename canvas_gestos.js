
const recursosCanvas = new WeakMap();
export default function ({data, parentElement, setTriggerValue}) {
    // Streamlit puede volver a ejecutar el renderer sin desmontar su contenedor.
    recursosCanvas.get(parentElement)?.();
    const plot = parentElement.querySelector('.ff-plot');
    const Plotly = window.Plotly;
    const fig = data.figura;
    const meta = fig.layout.meta;
    const posiciones = structuredClone(meta.posiciones);
    const vista = structuredClone(data.vista);
    const pointers = new Map();
    let nodo = null, cambiado = false, cerrado = false, frame = 0, timer = 0;
    let renderizando = false, pendiente = false, listo = false;
    const config = {responsive: true, displayModeBar: false, scrollZoom: false,
                    doubleClick: false, editable: false};

    function punto(u, v, curva, t) {
        const [x0, y0] = posiciones[u], [x1, y1] = posiciones[v];
        const dx = x1 - x0, dy = y1 - y0, largo = Math.hypot(dx, dy) || .001;
        const cx = (x0 + x1) / 2 - dy / largo * curva;
        const cy = (y0 + y1) / 2 + dx / largo * curva;
        return [(1-t)**2*x0 + 2*(1-t)*t*cx + t*t*x1,
                (1-t)**2*y0 + 2*(1-t)*t*cy + t*t*y1];
    }

    function geometria() {
        for (const e of meta.aristas) {
            const puntos = Array.from({length: 27}, (_, i) => punto(e.u, e.v, e.curva, (i+2)/30));
            fig.data[e.traza].x = puntos.map(p => p[0]);
            fig.data[e.traza].y = puntos.map(p => p[1]);
            const punta = punto(e.u, e.v, e.curva, .90), cola = punto(e.u, e.v, e.curva, .80);
            Object.assign(fig.layout.annotations[e.flecha], {x: punta[0], y: punta[1], ax: cola[0], ay: cola[1]});
            if (e.texto !== null) {
                const centro = punto(e.u, e.v, e.curva, .5);
                Object.assign(fig.layout.annotations[e.texto], {x: centro[0], y: centro[1]});
            }
        }
        const nodos = fig.data[fig.data.length - 1];
        nodos.x = meta.nodos.map(n => posiciones[n][0]);
        nodos.y = meta.nodos.map(n => posiciones[n][1]);
        fig.layout.xaxis.range = [...vista.x];
        fig.layout.yaxis.range = [...vista.y];
        fig.layout.datarevision = (fig.layout.datarevision || 0) + 1;
        fig.layout.uirevision = fig.layout.datarevision;
    }

    // Como máximo un render en curso: los eventos rápidos se agrupan por frame.
    function dibujar() {
        pendiente = true;
        if (frame || renderizando || cerrado) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            if (cerrado) return;
            pendiente = false;
            renderizando = true;
            geometria();
            Plotly.react(plot, fig.data, fig.layout, config).then(() => {
                renderizando = false;
                if (pendiente) dibujar();
            });
        });
    }

    function caja() {
        const r = plot.getBoundingClientRect();
        const m = fig.layout.margin;
        return {x: r.left + m.l, y: r.top + m.t,
                w: Math.max(1, r.width - m.l - m.r), h: Math.max(1, r.height - m.t - m.b)};
    }
    function coordenadas(p) {
        const b = caja();
        return [vista.x[0] + (p.x - b.x) / b.w * (vista.x[1] - vista.x[0]),
                vista.y[1] - (p.y - b.y) / b.h * (vista.y[1] - vista.y[0])];
    }
    function nodoCercano(p) {
        const b = caja();
        return meta.nodos.find(n => {
            const [x,y] = posiciones[n];
            const px = b.x + (x - vista.x[0]) / (vista.x[1] - vista.x[0]) * b.w;
            const py = b.y + (vista.y[1] - y) / (vista.y[1] - vista.y[0]) * b.h;
            return Math.hypot(px-p.x, py-p.y) <= 22;
        }) || null;
    }
    function mover(dx, dy) {
        const b = caja();
        const sx = dx / b.w * (vista.x[1] - vista.x[0]);
        const sy = dy / b.h * (vista.y[1] - vista.y[0]);
        vista.x = vista.x.map(v => v - sx);
        vista.y = vista.y.map(v => v + sy);
    }
    function zoom(factor, p) {
        // Límites numéricos para poder volver siempre a una vista útil.
        const ancho = vista.x[1] - vista.x[0];
        factor = Math.max(.08/ancho, Math.min(100/ancho, factor));
        const centro = coordenadas(p);
        vista.x = vista.x.map(v => centro[0] + (v - centro[0]) * factor);
        vista.y = vista.y.map(v => centro[1] + (v - centro[1]) * factor);
    }
    function guardar() {
        clearTimeout(timer);
        if (!cambiado || cerrado || pointers.size) return;
        cambiado = false;
        setTriggerValue('cambio', {revision: data.revision, posiciones, vista});
    }
    function down(e) {
        if (!listo || (e.pointerType === 'mouse' && ![0,2].includes(e.button))) return;
        e.preventDefault();
        clearTimeout(timer);
        const p = {x:e.clientX, y:e.clientY};
        pointers.set(e.pointerId, p);
        plot.setPointerCapture(e.pointerId);
        nodo = pointers.size === 1 && e.button !== 2 ? nodoCercano(p) : null;
        plot.style.cursor = 'grabbing';
    }
    function move(e) {
        if (!pointers.has(e.pointerId)) return;
        e.preventDefault();
        const anteriores = [...pointers.values()];
        const previo = pointers.get(e.pointerId), p = {x:e.clientX, y:e.clientY};
        pointers.set(e.pointerId, p);
        if (p.x === previo.x && p.y === previo.y) return;
        if (pointers.size === 2) {
            nodo = null;
            const actuales = [...pointers.values()];
            const centro = a => ({x:(a[0].x+a[1].x)/2, y:(a[0].y+a[1].y)/2});
            const distancia = a => Math.hypot(a[1].x-a[0].x, a[1].y-a[0].y);
            const ca = centro(anteriores), cn = centro(actuales);
            mover(cn.x-ca.x, cn.y-ca.y);
            zoom(Math.max(1,distancia(anteriores))/Math.max(1,distancia(actuales)), cn);
        } else if (pointers.size === 1 && nodo) {
            const a = coordenadas(previo), b = coordenadas(p);
            posiciones[nodo] = [posiciones[nodo][0]+b[0]-a[0], posiciones[nodo][1]+b[1]-a[1]];
        } else if (pointers.size === 1) {
            mover(p.x-previo.x, p.y-previo.y);
        }
        cambiado = true;
        dibujar();
    }
    function up(e) {
        if (!pointers.has(e.pointerId)) return;
        pointers.delete(e.pointerId);
        nodo = null;
        if (!pointers.size) {
            plot.style.cursor = 'grab';
            guardar();
        }
    }
    function wheel(e) {
        if (!listo) return;
        e.preventDefault();
        const delta = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 480 : 1);
        zoom(Math.exp(Math.max(-1,Math.min(1,delta*.002))), {x:e.clientX,y:e.clientY});
        cambiado = true;
        dibujar();
        clearTimeout(timer);
        timer = setTimeout(guardar, 250);
    }
    // Plotly escucha también touchstart/mousedown y crea una capa dragcover.
    // Interceptarlos evita que esa capa se lleve el segundo dedo del pinch.
    const bloquear = e => {e.preventDefault(); e.stopPropagation();};
    const handlers = {pointerdown:down, pointermove:move, pointerup:up,
                      pointercancel:up, lostpointercapture:up, wheel,
                      contextmenu:bloquear, dragstart:bloquear, mousedown:bloquear,
                      touchstart:bloquear, touchmove:bloquear, touchend:bloquear,
                      dblclick:bloquear};
    for (const [evento, fn] of Object.entries(handlers)) plot.addEventListener(evento, fn, {passive:false,capture:true});
    geometria();
    Plotly.newPlot(plot, fig.data, fig.layout, config).then(() => {if (!cerrado) listo = true;});
    const observer = new ResizeObserver(() => {if (listo && plot.clientWidth) Plotly.Plots.resize(plot);});
    observer.observe(plot);
    const limpiar = () => {
        cerrado = true;
        clearTimeout(timer);
        cancelAnimationFrame(frame);
        observer.disconnect();
        for (const [evento, fn] of Object.entries(handlers)) plot.removeEventListener(evento, fn, true);
        Plotly.purge(plot);
        recursosCanvas.delete(parentElement);
    };
    recursosCanvas.set(parentElement, limpiar);
    return () => {if (recursosCanvas.get(parentElement) === limpiar) limpiar();};
}
