import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { nombre, email, telefono, direccion, rfc, contacto_nombre, contacto_telefono, notas } = JSON.parse(event.body);
        
        // Validar campos requeridos
        if (!nombre) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'El nombre es requerido' })
            };
        }
        
        const result = await sql`
            INSERT INTO clientes (
                nombre, email, telefono, direccion, rfc, 
                contacto_nombre, contacto_telefono, notas
            ) VALUES (
                ${nombre}, ${email || null}, ${telefono || null}, 
                ${direccion || null}, ${rfc || null}, 
                ${contacto_nombre || null}, ${contacto_telefono || null}, 
                ${notas || null}
            ) RETURNING *
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                cliente: result[0]
            })
        };
        
    } catch (error) {
        console.error('Error creando cliente:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}