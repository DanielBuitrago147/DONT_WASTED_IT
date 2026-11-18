# estructuras.py
# Lógica de estructuras de datos avanzadas para DON'T WASTE IT

class Nodo:
    """ Nodo para el Árbol Binario de Búsqueda """
    def __init__(self, producto):
        self.producto = producto
        self.izquierdo = None
        self.derecho = None

class ArbolProductos:
    """ 
    Árbol Binario de Búsqueda para organizar los productos 
    de forma eficiente por precio (Menor a Mayor).
    """
    def __init__(self):
        self.raiz = None

    def insertar(self, producto):
        """ Inserta un nuevo producto comparando su precio de oferta """
        if not self.raiz:
            self.raiz = Nodo(producto)
        else:
            self._insertar_recursivo(self.raiz, producto)

    def _insertar_recursivo(self, nodo, producto):
        if producto['precio_oferta'] < nodo.producto['precio_oferta']:
            if nodo.izquierdo is None:
                nodo.izquierdo = Nodo(producto)
            else:
                self._insertar_recursivo(nodo.izquierdo, producto)
        else:
            if nodo.derecho is None:
                nodo.derecho = Nodo(producto)
            else:
                self._insertar_recursivo(nodo.derecho, producto)

    def obtener_lista_ordenada(self, nodo, lista):
        """ Retorna los productos ordenados mediante recorrido In-Order """
        if nodo:
            self.obtener_lista_ordenada(nodo.izquierdo, lista)
            lista.append(nodo.producto)
            self.obtener_lista_ordenada(nodo.derecho, lista)

class GrafoZonas:
    """ 
    Grafo para gestionar la cercanía geográfica entre 
    sectores y localidades.
    """
    def __init__(self):
        self.adyacencia = {
            'Norte': ['Norte', 'Centro'],
            'Centro': ['Norte', 'Sur', 'Centro', 'Este', 'Oeste', 'Suba', 'Kennedy', 'Zona 80'],
            'Sur': ['Centro', 'Sur'],
            'Este': ['Centro', 'Este'],
            'Oeste': ['Centro', 'Oeste'],
            'Suba': ['Suba', 'Centro'],
            'Kennedy': ['Kennedy', 'Centro'],
            'Zona 80': ['Zona 80', 'Centro']
        }

    def obtener_zonas_cercanas(self, zona_actual):
        """ Devuelve la lista de zonas colindantes """
        return self.adyacencia.get(zona_actual, [zona_actual])