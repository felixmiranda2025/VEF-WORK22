import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const cotizaciones = await sql`
            SELECT c.*, 
                   cl.nombre as cliente_nombre,
                   p.nombre as proyecto_nombre
            FROM cotizaciones c
            JOIN clientes cl ON c.cliente_id = cl.id
            LEFT JOIN proyectos p ON c.proyecto_id = p.id
            ORDER BY c.created_at DESC
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                cotizaciones: cotizaciones
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo cotizaciones:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}