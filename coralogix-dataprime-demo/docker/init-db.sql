-- E-commerce Database Schema
-- PostgreSQL initialization script for reinvent-ecommerce-demo

-- Drop existing tables if they exist
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on category for fast lookups (important for demo - shows index usage)
CREATE INDEX idx_products_category ON products(category);

-- Create index on price for range queries
CREATE INDEX idx_products_price ON products(price);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Create index on product_id for join performance
CREATE INDEX idx_orders_product_id ON orders(product_id);

-- Create index on user_id for user order lookups
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Seed products data (diverse categories for demo)
INSERT INTO products (name, category, price, stock_quantity, description, image_url) VALUES
-- Electronics
('Laptop Pro 15"', 'electronics', 1299.99, 50, 'High-performance laptop with 16GB RAM and 512GB SSD', 'https://example.com/laptop.jpg'),
('Wireless Mouse', 'electronics', 29.99, 200, 'Ergonomic wireless mouse with precision tracking', 'https://example.com/mouse.jpg'),
('USB-C Cable 6ft', 'electronics', 12.99, 500, 'Fast charging USB-C cable with reinforced connector', 'https://example.com/cable.jpg'),
('Bluetooth Headphones', 'electronics', 89.99, 150, 'Noise-cancelling Bluetooth headphones with 30hr battery', 'https://example.com/headphones.jpg'),
('4K Monitor 27"', 'electronics', 349.99, 80, 'Ultra HD 4K monitor with HDR support', 'https://example.com/monitor.jpg'),

-- Furniture
('Desk Chair', 'furniture', 249.99, 30, 'Comfortable ergonomic office chair with lumbar support', 'https://example.com/chair.jpg'),
('Standing Desk', 'furniture', 599.99, 15, 'Adjustable height standing desk with memory presets', 'https://example.com/desk.jpg'),
('Bookshelf 5-Tier', 'furniture', 129.99, 40, 'Sturdy wooden bookshelf with 5 adjustable shelves', 'https://example.com/bookshelf.jpg'),
('Floor Lamp', 'furniture', 79.99, 60, 'Modern LED floor lamp with adjustable brightness', 'https://example.com/lamp.jpg'),

-- Appliances
('Coffee Maker', 'appliances', 89.99, 75, 'Programmable 12-cup coffee maker with thermal carafe', 'https://example.com/coffee.jpg'),
('Blender 1000W', 'appliances', 59.99, 100, 'High-speed blender for smoothies and food processing', 'https://example.com/blender.jpg'),
('Microwave 1.1 Cu Ft', 'appliances', 119.99, 50, 'Compact microwave with 10 power levels', 'https://example.com/microwave.jpg'),
('Air Fryer 5Qt', 'appliances', 99.99, 90, 'Digital air fryer with 8 preset cooking functions', 'https://example.com/airfryer.jpg'),

-- Sports & Outdoors
('Running Shoes', 'sports', 119.99, 120, 'Lightweight running shoes with cushioned sole', 'https://example.com/shoes.jpg'),
('Yoga Mat', 'sports', 34.99, 80, 'Non-slip yoga mat with carrying strap', 'https://example.com/yogamat.jpg'),
('Water Bottle 32oz', 'sports', 24.99, 300, 'Insulated stainless steel water bottle', 'https://example.com/bottle.jpg'),
('Dumbbell Set', 'sports', 149.99, 45, 'Adjustable dumbbell set 5-50 lbs', 'https://example.com/dumbbells.jpg'),
('Resistance Bands', 'sports', 29.99, 150, 'Set of 5 resistance bands with door anchor', 'https://example.com/bands.jpg'),

-- Home & Kitchen
('Cookware Set 10-Piece', 'kitchen', 199.99, 35, 'Nonstick cookware set with glass lids', 'https://example.com/cookware.jpg'),
('Knife Set 15-Piece', 'kitchen', 79.99, 60, 'Professional kitchen knife set with block', 'https://example.com/knives.jpg'),
('Dinnerware Set 16-Piece', 'kitchen', 89.99, 50, 'Modern stoneware dinnerware for 4', 'https://example.com/dinnerware.jpg');

-- Seed some order data for popular products query demo
INSERT INTO orders (user_id, product_id, quantity, order_date) VALUES
('user-1001', 1, 1, NOW() - INTERVAL '5 days'),
('user-1002', 4, 1, NOW() - INTERVAL '4 days'),
('user-1003', 1, 1, NOW() - INTERVAL '3 days'),
('user-1004', 14, 2, NOW() - INTERVAL '3 days'),
('user-1005', 10, 1, NOW() - INTERVAL '2 days'),
('user-1006', 15, 1, NOW() - INTERVAL '2 days'),
('user-1007', 1, 1, NOW() - INTERVAL '1 day'),
('user-1008', 4, 1, NOW() - INTERVAL '1 day'),
('user-1009', 14, 1, NOW() - INTERVAL '1 day'),
('user-1010', 15, 3, NOW() - INTERVAL '6 hours');

-- Create a view for popular products (useful for analytics)
CREATE VIEW popular_products AS
SELECT 
    p.id,
    p.name,
    p.category,
    p.price,
    COUNT(o.id) as total_orders,
    SUM(o.quantity) as total_quantity_sold
FROM products p
LEFT JOIN orders o ON p.id = o.product_id
GROUP BY p.id, p.name, p.category, p.price
ORDER BY total_orders DESC;

-- Grant permissions (adjust as needed for your security requirements)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ecommerce_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ecommerce_user;
GRANT SELECT ON popular_products TO ecommerce_user;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'E-commerce database initialized successfully!';
    RAISE NOTICE 'Products: % rows', (SELECT COUNT(*) FROM products);
    RAISE NOTICE 'Orders: % rows', (SELECT COUNT(*) FROM orders);
END $$;
