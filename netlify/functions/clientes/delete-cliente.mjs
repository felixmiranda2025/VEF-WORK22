import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'DELETE') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { id } = JSON.parse(event.body);
        
        if (!id) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'ID requerido' })
            };
        }
        
        // Verificar si tiene proyectos asociados
        const proyectos = await sql`
            SELECT id FROM proyectos WHERE cliente_id = ${id} LIMIT 1
        `;
        
        if (proyectos.length > 0) {
            return {
                statusCode: 400,
                body: JSON.stringify({ 
                    success: false, 
                    error: 'No se puede eliminar el cliente porque tiene proyectos asociados' 
                })
            };
        }
        
        const result = await sql`
            DELETE FROM clientes 
            WHERE id = ${id}
            RETURNING id
        `;
        
        if (result.length === 0) {
            return {
                statusCode: 404,
                body: JSON.stringify({ success: false, error: 'Cliente no encontrado' })
            };
        }
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                message: 'Cliente eliminado correctamente'
            })
        };
        
    } catch (error) {
        console.error('Error eliminando cliente:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}