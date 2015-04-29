// my_appliances

var myAppliancesApp = angular.module('myAppliancesApp', []);

myAppliancesApp.config(function($interpolateProvider){
    $interpolateProvider.startSymbol('{[{').endSymbol('}]}');
});

myAppliancesApp.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';

}]);


myAppliancesApp.controller('EditVmName', function ($scope, $http, $timeout) {
    $scope.$watch("applianceOriginalName", function(){
        $scope.saved = {"name": $scope.applianceOriginalName};
        $scope.vm = {"name": $scope.saved.name};
    });
    $scope.editing = false;
    $scope.submitting = false;

    $scope.save = function(vm) {
        var responsePromise = $http.post(
            $scope.apiURL, {appliance_id: $scope.applianceId, new_name: vm.name});

        $scope.submitting = true;

        responsePromise.success(function(data, status, headers, config) {
            addAlert("success", "Task " + data + " queued.");
            $scope.taskId = data;
            (function waitUntilRenamed(){
                var taskFinishedPromise = $http.post($scope.taskResultURL, {task_id: $scope.taskId});
                taskFinishedPromise.success(function(data, status, headers, config) {
                    if(data !== null){
                        addAlert("success", "The appliance was renamed to " + data);
                        $scope.taskId = null;
                        $scope.vm.name = data;
                        $scope.saved.name = data;
                        $scope.submitting = false;
                        $scope.editing = false;
                    } else {
                        $timeout(waitUntilRenamed, 1000);
                    }
                });

                taskFinishedPromise.error(function(data, status, headers, config) {
                    addAlert("danger", "Could not rename the VM!");
                    $scope.submitting = false;
                });
            })();
        });

        responsePromise.error(function(data, status, headers, config) {
            addAlert("danger", data);
        });
     };

    $scope.cancel = function() {
       angular.copy($scope.saved, $scope.vm);
       $scope.editing = false;
     };

    $scope.edit = function() {
        $scope.vm = angular.copy($scope.saved);
        $scope.editing = true;
    };
});