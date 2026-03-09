import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const proyectos = await sql`
            SELECT p.*, c.nombre as cliente_nombre 
            FROM proyectos p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.created_at DESC
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                proyectos: proyectos
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo proyectos:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}