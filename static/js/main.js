function showAddToMealPlanModal(recipeId, recipeTitle) {
    document.getElementById('recipe_id').value = recipeId;
    const modal = new bootstrap.Modal(document.getElementById('addToMealPlanModal'));
    modal.show();
}

function showNutritionInfo(recipeId) {
    // Show loading state
    const nutritionModal = new bootstrap.Modal(document.getElementById('nutritionModal'));
    const modalBody = document.getElementById('nutritionModalBody');
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Loading nutrition information...</p></div>';
    nutritionModal.show();

    // Fetch nutrition information
    fetch(`/recipe_nutrition/${recipeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                modalBody.innerHTML = `
                    <div class="nutrition-info">
                        <h5 class="mb-3">Nutrition Facts</h5>
                        <div class="d-flex justify-content-between border-bottom py-2">
                            <span>Calories</span>
                            <strong>${data.nutrition.calories} kcal</strong>
                        </div>
                        <div class="d-flex justify-content-between border-bottom py-2">
                            <span>Protein</span>
                            <strong>${data.nutrition.protein}g</strong>
                        </div>
                        <div class="d-flex justify-content-between border-bottom py-2">
                            <span>Carbohydrates</span>
                            <strong>${data.nutrition.carbs}g</strong>
                        </div>
                        <div class="d-flex justify-content-between border-bottom py-2">
                            <span>Fat</span>
                            <strong>${data.nutrition.fat}g</strong>
                        </div>
                        <div class="mt-3">
                            <h6>Vitamins & Minerals</h6>
                            ${data.nutrition.nutrients.map(nutrient => `
                                <div class="d-flex justify-content-between small py-1">
                                    <span>${nutrient.name}</span>
                                    <span>${nutrient.amount}${nutrient.unit}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else {
                modalBody.innerHTML = '<div class="alert alert-danger">Failed to load nutrition information.</div>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            modalBody.innerHTML = '<div class="alert alert-danger">An error occurred while loading nutrition information.</div>';
        });
}

function changeView(viewType) {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('view', viewType);
    window.location.search = urlParams.toString();
}

function changeDate(date) {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('date', date);
    window.location.search = urlParams.toString();
}

function removeMeal(mealId) {
    if (confirm('Are you sure you want to remove this meal?')) {
        fetch(`/remove_meal/${mealId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert('Failed to remove meal: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to remove meal');
        });
    }
}

function printList() {
    const printContents = document.getElementById('grocery-list').innerHTML;
    const originalContents = document.body.innerHTML;
    
    document.body.innerHTML = `
        <div class="container mt-4">
            <h2>Shopping List</h2>
            ${printContents}
        </div>
    `;
    
    window.print();
    document.body.innerHTML = originalContents;
    
    // Reinitialize any Bootstrap components
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function showChangeMealModal(recipeId, recipeTitle) {
    // Reset the form and buttons
    document.getElementById('searchResults').classList.add('d-none');
    document.getElementById('searchRecipesForm').reset();
    document.getElementById('confirmChangeBtn').disabled = true;
    
    // Get the current date in YYYY-MM-DD format
    const today = new Date();
    const date = today.toISOString().split('T')[0];
    
    // Set default values
    document.getElementById('change_date').value = date;
    document.getElementById('change_meal_type').value = 'lunch'; // Default to lunch
    
    const modal = new bootstrap.Modal(document.getElementById('changeMealModal'));
    modal.show();
}

function searchRecipesForChange() {
    const ingredients = Array.from(document.getElementById('change_ingredients').selectedOptions)
                            .map(option => option.value);
    const diet = document.getElementById('change_diet').value;
    
    // Show loading state
    const resultsDiv = document.getElementById('recipeResults');
    resultsDiv.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Searching recipes...</p></div>';
    document.getElementById('searchResults').classList.remove('d-none');

    // Build query parameters
    const params = new URLSearchParams();
    if (ingredients.length > 0) {
        params.append('ingredients', ingredients.join(','));
    }
    if (diet) {
        params.append('diet', diet);
    }

    // Fetch recipes
    fetch(`/search_recipes_api?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultsDiv.innerHTML = data.recipes.map(recipe => `
                    <div class="col-md-4">
                        <div class="card h-100">
                            ${recipe.image ? `<img src="${recipe.image}" class="card-img-top" alt="${recipe.title}">` : ''}
                            <div class="card-body">
                                <h6 class="card-title">${recipe.title}</h6>
                                <p class="card-text"><small>Ready in ${recipe.readyInMinutes} minutes</small></p>
                                <button type="button" class="btn btn-sm btn-primary" 
                                        onclick="selectRecipeForChange('${recipe.id}')">
                                    Select
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                resultsDiv.innerHTML = '<div class="alert alert-danger">Failed to fetch recipes. Please try again.</div>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = '<div class="alert alert-danger">An error occurred while searching recipes.</div>';
        });
}

function selectRecipeForChange(recipeId) {
    document.getElementById('new_recipe_id').value = recipeId;
    document.getElementById('confirmChangeBtn').disabled = false;
    
    // Get the current date and meal type
    const date = document.getElementById('change_date').value;
    const mealType = document.getElementById('change_meal_type').value;
    
    // Create a form and submit it
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/change_meal';
    
    const recipeIdInput = document.createElement('input');
    recipeIdInput.type = 'hidden';
    recipeIdInput.name = 'new_recipe_id';
    recipeIdInput.value = recipeId;
    
    const dateInput = document.createElement('input');
    dateInput.type = 'hidden';
    dateInput.name = 'date';
    dateInput.value = date;
    
    const mealTypeInput = document.createElement('input');
    mealTypeInput.type = 'hidden';
    mealTypeInput.name = 'meal_type';
    mealTypeInput.value = mealType;
    
    form.appendChild(recipeIdInput);
    form.appendChild(dateInput);
    form.appendChild(mealTypeInput);
    
    document.body.appendChild(form);
    form.submit();
}

function showRecipeDetails(recipeId) {
    // Show loading state
    const recipeModal = new bootstrap.Modal(document.getElementById('recipeModal'));
    const modalBody = document.getElementById('recipeModalBody');
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Loading recipe details...</p></div>';
    recipeModal.show();

    // Fetch recipe details
    fetch(`/recipe_details/${recipeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const recipe = data.recipe;
                modalBody.innerHTML = `
                    <div class="recipe-details">
                        <h5 class="mb-3">${recipe.title}</h5>
                        <div class="recipe-info mb-3">
                            <span class="badge bg-primary me-2">Servings: ${recipe.servings}</span>
                            <span class="badge bg-info">Ready in: ${recipe.readyInMinutes} minutes</span>
                        </div>
                        <div class="ingredients mb-4">
                            <h6>Ingredients:</h6>
                            <ul class="list-unstyled">
                                ${recipe.ingredients.map(ingredient => `
                                    <li>
                                        <i class="fas fa-circle me-2 small"></i>
                                        ${ingredient.amount} ${ingredient.unit} ${ingredient.name}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                        <div class="instructions">
                            <h6>Instructions:</h6>
                            <p>${recipe.instructions}</p>
                        </div>
                    </div>
                `;
            } else {
                modalBody.innerHTML = '<div class="alert alert-danger">Failed to load recipe details.</div>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            modalBody.innerHTML = '<div class="alert alert-danger">An error occurred while loading recipe details.</div>';
        });
} 