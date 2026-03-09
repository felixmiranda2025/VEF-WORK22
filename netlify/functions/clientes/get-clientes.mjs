import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const clientes = await sql`
            SELECT * FROM clientes 
            ORDER BY nombre ASC
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                clientes: clientes
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo clientes:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}