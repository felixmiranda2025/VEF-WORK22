import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { nombre, contacto, email, telefono, direccion, rfc, condiciones_pago } = JSON.parse(event.body);
        
        if (!nombre) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'El nombre es requerido' })
            };
        }
        
        const result = await sql`
            INSERT INTO proveedores (
                nombre, contacto, email, telefono, direccion, rfc, condiciones_pago
            ) VALUES (
                ${nombre}, ${contacto || null}, ${email || null}, 
                ${telefono || null}, ${direccion || null}, 
                ${rfc || null}, ${condiciones_pago || null}
            ) RETURNING *
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                proveedor: result[0]
            })
        };
        
    } catch (error) {
        console.error('Error creando proveedor:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}