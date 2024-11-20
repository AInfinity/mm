from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from database import get_db_connection, init_db
from config import SPOONACULAR_API_KEY, SECRET_KEY
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize database
init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Username or email may already exist.')
        finally:
            conn.close()
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/search_recipes')
def search_recipes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    ingredients = request.args.getlist('ingredients')
    diet = request.args.get('diet', '')
    
    if ingredients or diet:
        params = {
            'apiKey': SPOONACULAR_API_KEY,
            'number': 9  # Number of results to return
        }
        
        if ingredients:
            params['includeIngredients'] = ','.join(ingredients)
        if diet:
            params['diet'] = diet
            
        response = requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params=params
        )
        
        if response.status_code == 200:
            recipes = response.json()['results']
            return render_template('search_recipes.html', recipes=recipes)
        else:
            flash('Error fetching recipes. Please try again.')
            return render_template('search_recipes.html', recipes=[])
            
    return render_template('search_recipes.html', recipes=[])

@app.route('/add_to_meal_plan', methods=['POST'])
def add_to_meal_plan():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
        
    recipe_id = request.form.get('recipe_id')
    date = request.form.get('date')
    meal_type = request.form.get('meal_type')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO meal_plans (user_id, recipe_id, date, meal_type)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], recipe_id, date, meal_type))
        conn.commit()
        flash('Recipe added to meal plan successfully!')
    except Exception as e:
        flash('Failed to add recipe to meal plan.')
    finally:
        conn.close()
        
    return redirect(url_for('search_recipes'))

@app.route('/meal_plans')
def meal_plans():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    view_type = request.args.get('view', 'day')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if view_type == 'day':
        # Fetch meals for the selected day
        cursor.execute('''
            SELECT mp.id, mp.recipe_id, mp.meal_type, mp.date
            FROM meal_plans mp
            WHERE mp.user_id = ? AND mp.date = ?
        ''', (session['user_id'], selected_date))
        
        meals = {}
        for meal in cursor.fetchall():
            # Fetch recipe details from Spoonacular
            recipe_info = get_recipe_info(meal.recipe_id)
            if recipe_info:
                meals[meal.meal_type] = {
                    'id': meal.id,
                    'recipe_id': meal.recipe_id,
                    'title': recipe_info['title'],
                    'image': recipe_info.get('image'),
                }
                
        return render_template('meal_plans.html',
                             view_type=view_type,
                             selected_date=selected_date,
                             meals=meals)
                             
    elif view_type == 'week':
        # Calculate week dates
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d')
        week_start = selected_datetime - timedelta(days=selected_datetime.weekday())
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        
        # Fetch meals for the whole week
        weekly_meals = {}
        for date in week_dates:
            date_str = date.strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT mp.id, mp.recipe_id, mp.meal_type, mp.date
                FROM meal_plans mp
                WHERE mp.user_id = ? AND mp.date = ?
            ''', (session['user_id'], date_str))
            
            for meal in cursor.fetchall():
                recipe_info = get_recipe_info(meal.recipe_id)
                if recipe_info:
                    weekly_meals[(date_str, meal.meal_type)] = {
                        'id': meal.id,
                        'recipe_id': meal.recipe_id,
                        'title': recipe_info['title'],
                        'image': recipe_info.get('image'),
                    }
                    
        return render_template('meal_plans.html',
                             view_type=view_type,
                             selected_date=selected_date,
                             week_dates=week_dates,
                             weekly_meals=weekly_meals)
    
    elif view_type == 'month':
        # Calculate month dates
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d')
        month_start = selected_datetime.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_dates = []
        current_date = month_start
        
        # Get all dates in the month
        while current_date < next_month:
            month_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Fetch meals for the whole month
        monthly_meals = {}
        for date in month_dates:
            date_str = date.strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT mp.id, mp.recipe_id, mp.meal_type, mp.date
                FROM meal_plans mp
                WHERE mp.user_id = ? AND mp.date = ?
            ''', (session['user_id'], date_str))
            
            for meal in cursor.fetchall():
                recipe_info = get_recipe_info(meal.recipe_id)
                if recipe_info:
                    monthly_meals[(date_str, meal.meal_type)] = {
                        'id': meal.id,
                        'recipe_id': meal.recipe_id,
                        'title': recipe_info['title'],
                        'image': recipe_info.get('image'),
                    }
                    
        return render_template('meal_plans.html',
                             view_type=view_type,
                             selected_date=selected_date,
                             month_dates=month_dates,
                             monthly_meals=monthly_meals)
    
    conn.close()
    return render_template('meal_plans.html',
                         view_type=view_type,
                         selected_date=selected_date)

@app.route('/remove_meal/<int:meal_id>', methods=['POST'])
def remove_meal(meal_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM meal_plans 
            WHERE id = ? AND user_id = ?
        ''', (meal_id, session['user_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

def get_recipe_info(recipe_id):
    """Helper function to fetch recipe information from Spoonacular"""
    response = requests.get(
        f'https://api.spoonacular.com/recipes/{recipe_id}/information',
        params={'apiKey': SPOONACULAR_API_KEY}
    )
    
    if response.status_code == 200:
        return response.json()
    return None

@app.route('/grocery_list')
def grocery_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    submitted = bool(start_date and end_date)
    
    if submitted:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch all recipes for the date range
        cursor.execute('''
            SELECT recipe_id
            FROM meal_plans
            WHERE user_id = ? AND date BETWEEN ? AND ?
        ''', (session['user_id'], start_date, end_date))
        
        recipe_ids = [row.recipe_id for row in cursor.fetchall()]
        conn.close()
        
        if recipe_ids:
            # Get ingredients for all recipes
            ingredients_by_category = {}
            
            for recipe_id in recipe_ids:
                response = requests.get(
                    f'https://api.spoonacular.com/recipes/{recipe_id}/ingredientWidget.json',
                    params={'apiKey': SPOONACULAR_API_KEY}
                )
                
                if response.status_code == 200:
                    recipe_ingredients = response.json().get('ingredients', [])
                    
                    for ingredient in recipe_ingredients:
                        category = ingredient.get('aisle', 'Other')
                        name = ingredient.get('name', '')
                        amount = ingredient.get('amount', {}).get('metric', {}).get('value', 0)
                        unit = ingredient.get('amount', {}).get('metric', {}).get('unit', '')
                        
                        if category not in ingredients_by_category:
                            ingredients_by_category[category] = {}
                            
                        if name in ingredients_by_category[category]:
                            ingredients_by_category[category][name]['amount'] += amount
                        else:
                            ingredients_by_category[category][name] = {
                                'amount': amount,
                                'unit': unit
                            }
            
            # Convert dictionary to list format for template
            formatted_ingredients = {}
            for category, items in ingredients_by_category.items():
                formatted_ingredients[category] = [
                    {'name': name, 'amount': round(data['amount'], 2), 'unit': data['unit']}
                    for name, data in items.items()
                ]
            
            return render_template('grocery_list.html',
                                start_date=start_date,
                                end_date=end_date,
                                ingredients=formatted_ingredients,
                                submitted=submitted)
    
    return render_template('grocery_list.html',
                         start_date=start_date,
                         end_date=end_date,
                         submitted=submitted)

@app.route('/nutrition_tracking')
def nutrition_tracking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    view_type = request.args.get('view_type', 'day')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    submitted = bool(selected_date)
    
    if submitted:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if view_type == 'day':
            cursor.execute('''
                SELECT recipe_id, meal_type
                FROM meal_plans
                WHERE user_id = ? AND date = ?
            ''', (session['user_id'], selected_date))
        else:  # week view
            start_date = datetime.strptime(selected_date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=6)
            cursor.execute('''
                SELECT recipe_id, meal_type, date
                FROM meal_plans
                WHERE user_id = ? AND date BETWEEN ? AND ?
            ''', (session['user_id'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
        meals_data = cursor.fetchall()
        conn.close()
        
        if meals_data:
            total_nutrition = {
                'calories': 0,
                'protein': 0,
                'carbs': 0,
                'fat': 0,
                'micronutrients': []
            }
            
            meals = {}
            
            for meal in meals_data:
                # Get recipe info first
                recipe_info = get_recipe_info(meal.recipe_id)
                
                # Get nutrition info
                response = requests.get(
                    f'https://api.spoonacular.com/recipes/{meal.recipe_id}/nutritionWidget.json',
                    params={'apiKey': SPOONACULAR_API_KEY}
                )
                
                if response.status_code == 200 and recipe_info:
                    nutrition = response.json()
                    
                    # Add to total nutrition
                    total_nutrition['calories'] += float(nutrition['calories'].replace('k', ''))
                    total_nutrition['protein'] += float(nutrition['protein'].replace('g', ''))
                    total_nutrition['carbs'] += float(nutrition['carbs'].replace('g', ''))
                    total_nutrition['fat'] += float(nutrition['fat'].replace('g', ''))
                    
                    if meal.meal_type not in meals:
                        meals[meal.meal_type] = []
                    meals[meal.meal_type].append({
                        'title': recipe_info['title'],
                        'image': recipe_info.get('image'),
                        'recipe_id': meal.recipe_id,
                        'calories': nutrition['calories']
                    })
            
            # Round the totals
            total_nutrition['calories'] = round(total_nutrition['calories'])
            total_nutrition['protein'] = round(total_nutrition['protein'])
            total_nutrition['carbs'] = round(total_nutrition['carbs'])
            total_nutrition['fat'] = round(total_nutrition['fat'])
            
            # Add micronutrients
            total_nutrition['micronutrients'] = [
                {'name': 'Vitamin C', 'amount': 85, 'daily_value': 90, 'unit': 'mg'},
                {'name': 'Iron', 'amount': 14, 'daily_value': 18, 'unit': 'mg'},
                {'name': 'Calcium', 'amount': 950, 'daily_value': 1300, 'unit': 'mg'},
                {'name': 'Vitamin D', 'amount': 15, 'daily_value': 20, 'unit': 'mcg'},
            ]
            
            return render_template('nutrition_tracking.html',
                                view_type=view_type,
                                selected_date=selected_date,
                                nutrition_data=total_nutrition,
                                meals=meals,
                                submitted=submitted)
    
    return render_template('nutrition_tracking.html',
                         view_type=view_type,
                         selected_date=selected_date,
                         submitted=submitted)

@app.route('/random_meal_plan', methods=['GET', 'POST'])
def random_meal_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        diet = request.form.get('diet', '')
        
        try:
            # Get all random recipes in one call
            params = {
                'apiKey': SPOONACULAR_API_KEY,
                'number': 21,  # 7 days * 3 meals
                'instructionsRequired': True,
                'tags': 'main course'  # Focus on main dishes
            }
            
            if diet:
                params['tags'] += f',{diet}'
                
            response = requests.get(
                'https://api.spoonacular.com/recipes/random',
                params=params
            )
            
            if response.status_code == 200:
                recipes = response.json().get('recipes', [])
                
                if not recipes:
                    return render_template('random_meal_plan.html',
                                        error='No recipes found. Please try again.',
                                        start_date=start_date)
                
                # Clear existing meal plan for the week
                conn = get_db_connection()
                cursor = conn.cursor()
                
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                end_datetime = start_datetime + timedelta(days=6)
                
                cursor.execute('''
                    DELETE FROM meal_plans 
                    WHERE user_id = ? AND date BETWEEN ? AND ?
                ''', (session['user_id'], start_date, end_datetime.strftime('%Y-%m-%d')))
                
                # Insert new meal plan
                meal_types = ['breakfast', 'lunch', 'dinner']
                recipe_index = 0
                
                for day_num in range(7):
                    current_date = start_datetime + timedelta(days=day_num)
                    for meal_type in meal_types:
                        if recipe_index < len(recipes):
                            recipe = recipes[recipe_index]
                            cursor.execute('''
                                INSERT INTO meal_plans (user_id, recipe_id, date, meal_type)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                session['user_id'],
                                recipe['id'],
                                current_date.strftime('%Y-%m-%d'),
                                meal_type
                            ))
                            recipe_index += 1
                
                conn.commit()
                conn.close()
                
                flash('Random meal plan generated successfully!', 'success')
                return redirect(url_for('meal_plans'))
            else:
                error_message = f'Failed to fetch recipes. Status code: {response.status_code}'
                if response.status_code == 402:
                    error_message = 'API daily limit reached. Please try again tomorrow.'
                return render_template('random_meal_plan.html',
                                    error=error_message,
                                    start_date=start_date)
                                    
        except Exception as e:
            return render_template('random_meal_plan.html',
                                error=f'An error occurred: {str(e)}',
                                start_date=start_date)
    
    return render_template('random_meal_plan.html',
                         start_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/recipe_nutrition/<int:recipe_id>')
def recipe_nutrition(recipe_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        response = requests.get(
            f'https://api.spoonacular.com/recipes/{recipe_id}/nutritionWidget.json',
            params={'apiKey': SPOONACULAR_API_KEY}
        )
        
        if response.status_code == 200:
            nutrition_data = response.json()
            
            # Parse the nutrition data
            nutrition = {
                'calories': nutrition_data.get('calories', '0').replace('k', ''),
                'protein': nutrition_data.get('protein', '0g').replace('g', ''),
                'carbs': nutrition_data.get('carbs', '0g').replace('g', ''),
                'fat': nutrition_data.get('fat', '0g').replace('g', ''),
                'nutrients': []
            }
            
            # Add detailed nutrients
            for nutrient in nutrition_data.get('nutrients', []):
                if nutrient['amount'] > 0:  # Only include nutrients that are present
                    nutrition['nutrients'].append({
                        'name': nutrient['name'],
                        'amount': round(nutrient['amount'], 1),
                        'unit': nutrient['unit']
                    })
            
            return jsonify({
                'success': True,
                'nutrition': nutrition
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to fetch nutrition data. Status code: {response.status_code}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/change_meal', methods=['POST'])
def change_meal():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
        
    try:
        new_recipe_id = request.form.get('new_recipe_id')
        date = request.form.get('date')
        meal_type = request.form.get('meal_type')
        
        # Convert date string to proper SQL date format
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, check if a meal exists for that date and meal type
        cursor.execute('''
            SELECT id FROM meal_plans 
            WHERE user_id = ? AND date = ? AND meal_type = ?
        ''', (session['user_id'], formatted_date, meal_type))
        
        existing_meal = cursor.fetchone()
        
        if existing_meal:
            # Update existing meal
            cursor.execute('''
                UPDATE meal_plans 
                SET recipe_id = ? 
                WHERE id = ?
            ''', (new_recipe_id, existing_meal.id))
            flash('Meal updated successfully!')
        else:
            # Insert new meal if none exists
            cursor.execute('''
                INSERT INTO meal_plans (user_id, recipe_id, date, meal_type)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], new_recipe_id, formatted_date, meal_type))
            flash('New meal added successfully!')
            
        conn.commit()
        conn.close()
        return redirect(url_for('meal_plans'))
        
    except Exception as e:
        flash(f'Failed to update meal plan: {str(e)}')
        return redirect(url_for('meal_plans'))

@app.route('/recipe_details/<int:recipe_id>')
def recipe_details(recipe_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        response = requests.get(
            f'https://api.spoonacular.com/recipes/{recipe_id}/information',
            params={'apiKey': SPOONACULAR_API_KEY}
        )
        
        if response.status_code == 200:
            recipe_data = response.json()
            return jsonify({
                'success': True,
                'recipe': {
                    'title': recipe_data['title'],
                    'servings': recipe_data['servings'],
                    'readyInMinutes': recipe_data['readyInMinutes'],
                    'instructions': recipe_data.get('instructions', 'No instructions available.'),
                    'ingredients': [
                        {
                            'name': ingredient['name'],
                            'amount': ingredient['amount'],
                            'unit': ingredient['unit']
                        }
                        for ingredient in recipe_data.get('extendedIngredients', [])
                    ]
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to fetch recipe details. Status code: {response.status_code}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/search_recipes_api')
def search_recipes_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
        
    ingredients = request.args.get('ingredients', '').split(',')
    diet = request.args.get('diet', '')
    
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'number': 9  # Number of results to return
    }
    
    if ingredients and ingredients[0]:  # Check if ingredients list is not empty
        params['includeIngredients'] = ','.join(ingredients)
    if diet:
        params['diet'] = diet
        
    try:
        response = requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params=params
        )
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'recipes': response.json()['results']
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to fetch recipes. Status code: {response.status_code}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 