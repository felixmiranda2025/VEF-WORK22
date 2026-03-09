import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const proveedores = await sql`
            SELECT * FROM proveedores 
            ORDER BY nombre ASC
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                proveedores: proveedores
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo proveedores:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}