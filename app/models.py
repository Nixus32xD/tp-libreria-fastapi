"""Import every table without loading the application or creating an engine."""

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

__all__ = [
    "Autor",
    "Cliente",
    "Editorial",
    "Genero",
    "Libro",
    "LibroAutor",
    "PerfilCliente",
    "RenglonVenta",
    "Venta",
]
