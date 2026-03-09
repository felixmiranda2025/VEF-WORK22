import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { id } = event.queryStringParameters || {};
        
        if (!id) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'ID requerido' })
            };
        }
        
        const clientes = await sql`
            SELECT * FROM clientes 
            WHERE id = ${id}
        `;
        
        if (clientes.length === 0) {
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
                cliente: clientes[0]
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo cliente:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}